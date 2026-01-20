from typing import Optional, List

from langchain_core.tools import BaseTool
from pydantic import create_model, Field

from agent.utils.db_utils import MySQLDatabaseManager
from agent.utils.log_utils import log


class ListTablesTool(BaseTool):

    name:str="sql_db_list_tables"
    description:str="列出MySQL数据库中所有表名及描述信息"

    db_manager:MySQLDatabaseManager

    def _run(self) ->str:
        try:
            tables_info=self.db_manager.get_tables_with_comments()
            result= f"数据库中共有{len(tables_info)} 个表：\n\n"
            for i,table_info in enumerate(tables_info):
                table_name = table_info['table_name']
                table_comment = table_info['table_comment']

                if not table_comment or table_comment.isspace():
                    description_display="暂无描述"
                else:
                    description_display = table_comment

                result +=f"{i+1}. 表名：{table_name}\n"
                result +=f"  描述：{description_display}\n\n"
            return result
        except Exception as e:
            log.exception(e)
            return f"列出表时出错：{str(e)}"

    async def _arun(self)->str:
        return self._run()

class TableSchemaTool(BaseTool):

    name:str="sql_db_schema"
    description:str="获取MySQL数据库表中指定表的详细模式信息，包括列定义、主键、外键等。输入应为逗号分隔的表名列表，以获取所有表信息。"

    db_manager:MySQLDatabaseManager

    def __init__(self,**kwargs) :
        super().__init__(**kwargs)
        # self.db_manager=db_manager
        self.args_schema=create_model(
            "TableSchemaToolArgs",
        table_names=(Optional[str], Field(..., description='逗号分隔的表名列表，例如：t_rolemodel, t_student')))

    def _run(self,table_names:Optional[str]=None)->str:

        try:
            table_list=None
            if table_names:
                table_list=[name.strip() for name in table_names.split(',') if name.strip()]
            schema_info=self.db_manager.get_table_schema(table_list)
            return schema_info if schema_info else "未找到匹配的表"
        except Exception as e:
            log.exception(e)
            return f"获取表模式信息时出错：{str(e)}"

    async def _arun(self,table_names:Optional[str]=None)->str:
        return self._run(table_names)

class SQLQueryTool(BaseTool):
    """执行SQL查询"""
    name: str = "sql_db_query"
    description: str = "在MySQL数据库上执行安全的SELECT查询并返回结果。输入应为有效的SQL SELECT查询语句。"
    db_manager: MySQLDatabaseManager

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.db_manager = db_manager
        self.args_schema = create_model("SQLQueryToolArgs",
                                        query=(str, Field(..., description="有效的SQL查询语句")))

    def _run(self, query: str = None) -> str:
        """执行工具逻辑"""
        try:
            if query is None:
                return "错误：未提供查询语句"
            result = self.db_manager.execute_query(query)
            return result
        except Exception as e:
            return f"执行查询时出错: {str(e)}"

    async def _arun(self, query: str = None) -> str:
        """异步执行"""
        return self._run(query)

class SQLQueryCheckerTool(BaseTool):
    """检查SQL查询语法"""
    name: str = "sql_db_query_checker"
    description: str = "检查SQL查询语句的语法是否正确，提供验证反馈。输入应为要检查的SQL查询。参数格式: {'query': 'SQL查询语句'}"
    db_manager: MySQLDatabaseManager

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.db_manager = db_manager
        self.args_schema = create_model("SQLQueryCheckerToolArgs",
                                        query=(str, Field(..., description="需要进行检查的sql语句")))

    def _run(self, query: str = None) -> str:
        """执行工具逻辑"""
        try:
            if query is None:
                return "错误：未提供查询语句"
            result = self.db_manager.validate_query(query)
            return result
        except Exception as e:
            return f"检查查询时出错: {str(e)}"

    async def _arun(self, query: str = None) -> str:
        """异步执行"""
        return self._run(query)



if __name__ == '__main__':
    username = 'root'
    password = '111111'
    host = '127.0.0.2'
    port = 3306
    database = 'mytestdb'

    connection_string = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    manager = MySQLDatabaseManager(connection_string)
    # tool=ListTablesTool(db_manager=manager) #测试第一个工具
    # print(tool.invoke({}))
    # tool=TableSchemaTool(db_manager=manager) #测试第二个工具
    # print(tool.invoke({'table_names':[ 't_student','t_rolemodel']}))
    # tool = SQLQueryTool(db_manager=manager)  # 测试第三个工具
    # print(tool.invoke({'query':"select * from t_rolemodel"}))
    # tool = SQLQueryCheckerTool(db_manager=manager)  # 测试第四个工具
    # print(tool.invoke({'query': 'select count(*) from t_rolemodel'}))