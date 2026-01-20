from typing import List
from langchain.agents import create_agent
from langchain_core.tools import BaseTool
from agent.toots.test_to_sql_tools import ListTablesTool, SQLQueryTool, SQLQueryCheckerTool
from agent.toots.test_to_sql_tools import TableSchemaTool
from agent.utils.db_utils import MySQLDatabaseManager
from agent.my_llm import llm

def get_tools(host:str, port:int, username:str, password:str,database:str)->List[BaseTool]:
    connection_string = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    manager = MySQLDatabaseManager(connection_string)
    return [
        ListTablesTool(db_manager=manager),
        TableSchemaTool(db_manager=manager),
        SQLQueryTool(db_manager=manager),
        SQLQueryCheckerTool(db_manager=manager)
    ]


#系统提示词
system_prompt ="""
你是一个专门设计用于与SQL数据库交互的AI智能体。

给定一个输入问题，你需要按照以下步骤操作：
1. 创建一个语法正确的{dialect}查询语句
2. 每次都要进行查询sql语句验证
3. 然后在执行查询并查看结果
4. 基于查询结果返回最终答案

除非用户明确指定要获取的具体示例数量，否则始终将查询结果限制为最多{top_k}条。

你可以通过相关列对结果进行排序，以返回数据库中最有意义的示例。
永远不要查询特定表的所有列，只获取与问题相关的列。

在执行查询之前，你必须仔细检查查询语句。如果在执行查询时遇到错误，请重写查询并再次尝试。

绝对不要对数据库执行任何数据操作语言（DML）语句（如INSERT、UPDATE、DELETE、DROP等）。

开始处理问题时，你应该始终先查看数据库中有哪些表可以查询。不要跳过这一步。
然后，你应该查询最相关表的模式结构信息
""".format(
    dialect='MYSQL',
    top_k=5,
)

tools=get_tools('127.0.0.2', 3306, username = 'root', password = '111111', database = 'mytestdb')


agent=create_agent(
    llm,
    tools=tools,
    system_prompt=system_prompt
)
for result in agent.stream(
        input={"messages": [{"role": "user", "content": "数据库中丘丘的年龄"}]},
        stream_mode="values"
):
    result["messages"][-1].pretty_print()