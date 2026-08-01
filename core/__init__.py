import pymysql

pymysql.install_as_MySQLdb()
pymysql.version_info = (1, 4, 6, "final", 0)  # 兼容 Django 版本检查
