import json
from typing import List, Optional

from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.expression import text

from agent.utils.log_utils import log


class MySQLDatabaseManager:
    """MySQL数据库管理器，负责数据库连接和基本操作"""

    def __init__(self, connection_string: str):
        """
        初始化MySQL数据库连接

        Args:
            connection_string: MySQL连接字符串，格式为:
                mysql+pymysql://username:password@host:port/database
        """
        self.engine = create_engine(connection_string, pool_size=5, pool_recycle=3600)

    def get_table_names(self) -> list[str]:
        """
        获取数据库中所有表的名称

        Returns:
            列表，包含数据库中所有表的名称
        """
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except Exception as e:
            log.exception(e)
            raise ValueError(f"获取表名失败：{str(e)}")

    def get_tables_with_comments(self) -> List[dict]:
        """
        获取数据库中所有表的名称和描述信息。

        Returns:
            List[dict]: 一个字典列表，每个字典包含 'table_name' 和 'table_comment' 键。
        """
        try:
            # 构建查询语句，从 INFORMATION_SCHEMA.TABLES 中获取表名和注释
            query = text("""
                         SELECT TABLE_NAME, TABLE_COMMENT
                         FROM INFORMATION_SCHEMA.TABLES
                         WHERE TABLE_SCHEMA = DATABASE()
                           AND TABLE_TYPE = 'BASE TABLE'
                         ORDER BY TABLE_NAME
                         """)

            with self.engine.connect() as connection:
                result = connection.execute(query)
                # 将结果转换为字典列表，便于后续处理
                tables_info = [{'table_name': row[0], 'table_comment': row[1]} for row in result]
                return tables_info

        except SQLAlchemyError as e:
            log.error(e)
            raise ValueError(f"获取表名及描述信息失败：{str(e)}")

    def get_table_schema(self, table_names: Optional[List[str]] = None) -> str:
        """
        获取指定表的模式信息（包含字段注释）

        Args:
            table_names: 表名列表，如果为None则获取所有表
        """
        try:
            inspector = inspect(self.engine)
            schema_info = []

            tables_to_process = table_names if table_names else self.get_table_names()

            for table_name in tables_to_process:
                # 获取表结构信息
                columns = inspector.get_columns(table_name)

                # 使用 get_pk_constraint 替代已弃用的 get_primary_keys
                pk_constraint = inspector.get_pk_constraint(table_name)
                primary_keys = pk_constraint['constrained_columns'] if pk_constraint else []

                foreign_keys = inspector.get_foreign_keys(table_name)
                indexes = inspector.get_indexes(table_name)

                # 构建表模式描述
                table_schema = f"表名: {table_name}\n"
                table_schema += "列信息:\n"

                for column in columns:
                    # 检查该列是否在主键列表中
                    pk_indicator = " (主键)" if column['name'] in primary_keys else ""
                    # 获取字段注释，如果不存在则显示“无注释”
                    comment = column.get('comment', '无注释')
                    table_schema += f"  - {column['name']}: {str(column['type'])}{pk_indicator} [注释: {comment}]\n"

                if foreign_keys:
                    table_schema += "外键约束:\n"
                    for fk in foreign_keys:
                        table_schema += f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}\n"

                if indexes:
                    table_schema += "索引信息:\n"
                    for idx in indexes:
                        if not idx['name'].startswith('sqlite_'):
                            table_schema += f"  - {idx['name']}: {idx['column_names']} ({'唯一' if idx['unique'] else '非唯一'})\n"

                schema_info.append(table_schema)

            return "\n".join(schema_info) if schema_info else "未找到匹配的表"

        except SQLAlchemyError as e:
            log.error(e)
            raise ValueError(f"获取表模式失败: {str(e)}")

    def execute_query(self, query: str) -> str:
        """
        执行SQL查询并返回结果

        Args:
            query: SQL查询语句
        """
        # 安全检查：防止数据修改操作
        forbidden_keywords = ['insert', 'update', 'delete', 'drop', 'alter', 'create', 'grant', 'truncate']
        query_lower = query.lower().strip()

        # 检查是否以SELECT开头（允许子查询等复杂情况）
        if not query_lower.startswith(('select', 'with')) and any(
                keyword in query_lower for keyword in forbidden_keywords):
            raise ValueError("出于安全考虑，只允许执行SELECT查询和WITH查询")

        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(query))

                # 获取列名
                columns = result.keys()

                # 获取数据（限制返回行数防止内存溢出）
                rows = result.fetchmany(100)

                if not rows:
                    return "查询结果为空"

                # 格式化结果
                result_data = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        # 处理无法序列化的数据类型
                        try:
                            # 尝试JSON序列化来检测是否可序列化
                            if row[i] is not None:
                                json.dumps(row[i])
                            row_dict[col] = row[i]
                        except (TypeError, ValueError):
                            row_dict[col] = str(row[i])
                    result_data.append(row_dict)

                return json.dumps(result_data, ensure_ascii=False, indent=2)
        except SQLAlchemyError as e:
            log.error(e)
            raise ValueError(f"sql执行错误：{str(e)}")

    def validate_query(self, query: str) -> str:
        """
        验证SQL查询语法是否正确

        Args:
            query: 要验证的SQL查询
        """
        # 基本语法检查
        if not query or not query.strip():
            return "错误：查询不能为空"

        # 检查是否以SELECT或WITH开头
        query_lower = query.lower().strip()
        if not query_lower.startswith(('select', 'with')):
            return "警告：建议使用SELECT或WITH查询，其他操作可能被限制"

        try:
            with self.engine.connect() as connection:
                if self.engine.dialect.name == 'mysql':
                    explain_query = text(f"EXPLAIN {query}")  # 这里的query
                else:
                    explain_query = text(f"EXPLAIN {query}")
                connection.execute(explain_query)
                return "SQL查询语法正确(已通过数据库EXPLAIN验证)"
        except Exception as e:
            log.error(e)
            return f"SQL语法错误: {str(e)}"


if __name__ == '__main__':
    username='root'
    password='111111'
    host='127.0.0.2'
    port=3306
    database='mytestdb'

    connection_string=f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    manager=MySQLDatabaseManager(connection_string)

    # print(manager.get_table_names())
    print(manager.get_tables_with_comments())