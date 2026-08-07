from django.db import models


class ScanRun(models.Model):
    """一次硬编码扫描运行记录"""

    STATUS_CHOICES = [
        ("running", "扫描中"),
        ("finished", "完成"),
        ("failed", "失败"),
    ]
    SOURCE_CHOICES = [
        ("project", "当前项目"),
        ("path", "本地路径"),
        ("url", "Git 仓库 URL"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="finished", verbose_name="状态")
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="project", verbose_name="目标类型")
    target_path = models.CharField(max_length=1000, blank=True, default="", verbose_name="扫描目标")
    files_scanned = models.IntegerField(default=0, verbose_name="扫描文件数")
    findings_count = models.IntegerField(default=0, verbose_name="发现数")
    duration_ms = models.IntegerField(default=0, verbose_name="耗时(ms)")
    error_message = models.CharField(max_length=500, blank=True, default="", verbose_name="错误信息")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="扫描时间")

    class Meta:
        db_table = "secret_scan_run"
        ordering = ["-created_at"]
        verbose_name = "扫描记录"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"扫描 #{self.pk} {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}（{self.findings_count} 处）"


class SecretFinding(models.Model):
    """单条硬编码密钥发现"""

    STATUS_CHOICES = [
        ("open", "待处理"),
        ("false_positive", "误报"),
        ("fixed", "已修复"),
    ]
    SEVERITY_CHOICES = [
        ("critical", "严重"),
        ("high", "高"),
        ("medium", "中"),
        ("low", "低"),
    ]

    scan_run = models.ForeignKey(
        ScanRun, related_name="findings", on_delete=models.CASCADE,
        null=True, blank=True, verbose_name="所属扫描",
    )
    rule_id = models.CharField(max_length=100, verbose_name="规则ID")
    rule_name = models.CharField(max_length=200, verbose_name="规则")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="medium", verbose_name="级别")
    file_path = models.CharField(max_length=500, verbose_name="文件")
    line_number = models.IntegerField(default=0, verbose_name="行号")
    line_text = models.CharField(max_length=500, blank=True, default="", verbose_name="行内容")
    secret_preview = models.CharField(max_length=200, verbose_name="脱敏密钥")
    entropy = models.FloatField(default=0, verbose_name="熵值")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open", verbose_name="处理状态")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="发现时间")

    class Meta:
        db_table = "secret_finding"
        ordering = ["-created_at", "file_path", "line_number"]
        verbose_name = "密钥发现"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.rule_name} @ {self.file_path}:{self.line_number}"
