from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
    verbose_name = "热点数据采集"

    def ready(self):
        # 服务重启后自动恢复数据库中已启用的调度任务（抖音/微博热搜爬虫等）
        from tools.scheduler import restore_jobs_from_config

        restore_jobs_from_config()
