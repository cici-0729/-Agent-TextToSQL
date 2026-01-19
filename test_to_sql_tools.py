from langchain_core.tools import BaseTool
from sqlalchemy.dialects.mssql.information_schema import tables

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
            log.exection(e)
            return f"列出表时出错：{str(e)}"

    async def _arun(self)->str:
        return self._run()

if __name__ == '__main__':
    username = 'root'
    password = '111111'
    host = '127.0.0.2'
    port = 3306
    database = 'mytestdb'

    connection_string = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    manager = MySQLDatabaseManager(connection_string)
    tool=ListTablesTool(db_manager=manager)
    print(tool.invoke({}))