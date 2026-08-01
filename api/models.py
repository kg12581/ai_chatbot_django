from django.db import models


class DouyinHotSearch(models.Model):
    """抖音热搜榜数据"""

    LABEL_CHOICES = [
        ("hot", "热"),
        ("new", "新"),
        ("boil", "沸"),
        ("normal", ""),
    ]

    rank = models.IntegerField(verbose_name="排名")
    title = models.CharField(max_length=500, verbose_name="热搜标题")
    hot_value = models.BigIntegerField(default=0, verbose_name="热度值")
    label = models.CharField(max_length=20, default="normal", verbose_name="标签")
    cover_url = models.URLField(max_length=1000, blank=True, default="", verbose_name="封面图")
    crawl_batch = models.DateTimeField(verbose_name="爬取批次时间")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="入库时间")

    class Meta:
        db_table = "douyin_hot_search"
        ordering = ["rank"]
        verbose_name = "抖音热搜"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"#{self.rank} {self.title} ({self.hot_value})"

    @property
    def label_display(self):
        return dict(self.LABEL_CHOICES).get(self.label, "")


class SchedulerConfig(models.Model):
    """定时调度配置"""

    TASK_CHOICES = [
        ("douyin_hot_crawler", "抖音热搜爬虫"),
    ]

    task_id = models.CharField(max_length=100, unique=True, verbose_name="任务标识")
    task_name = models.CharField(max_length=200, verbose_name="任务名称")
    func_path = models.CharField(max_length=500, verbose_name="执行函数路径")
    cron_expr = models.CharField(max_length=200, default="0 * * * *", verbose_name="cron表达式")
    enabled = models.BooleanField(default=False, verbose_name="是否启用")

    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name="上次执行时间")
    last_run_result = models.CharField(max_length=500, blank=True, default="", verbose_name="上次执行结果")
    run_count = models.IntegerField(default=0, verbose_name="总执行次数")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "scheduler_config"
        verbose_name = "调度配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.task_name} ({self.cron_expr}) [{'ON' if self.enabled else 'OFF'}]"
