"""MCP 服务器与 Skill 配置模型。

- McpServer: 外部 MCP 服务器配置（stdio/sse/http）
- McpTool: 项目内自建 MCP 工具（Python 函数封装）
- Skill: 可配置的 Prompt 模板（对话时按需激活）
"""

from django.db import models


class McpServer(models.Model):
    """外部 MCP 服务器配置。"""

    TRANSPORT_CHOICES = [
        ("stdio", "STDIO（本地进程）"),
        ("sse", "SSE（Server-Sent Events）"),
        ("streamable_http", "Streamable HTTP"),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="名称")
    description = models.CharField(max_length=500, blank=True, default="", verbose_name="描述")
    transport = models.CharField(
        max_length=20, choices=TRANSPORT_CHOICES, default="stdio", verbose_name="传输方式"
    )
    command = models.CharField(
        max_length=500, blank=True, default="",
        verbose_name="启动命令",
        help_text="STDIO 模式：可执行文件路径，如 npx -y @modelcontextprotocol/server-filesystem /tmp"
    )
    url = models.URLField(
        max_length=500, blank=True, default="",
        verbose_name="服务地址",
        help_text="SSE/HTTP 模式：http://host:port/sse"
    )
    env_vars = models.TextField(
        blank=True, default="",
        verbose_name="环境变量",
        help_text="JSON 格式，如 {\"API_KEY\": \"xxx\"}"
    )
    enabled = models.BooleanField(default=False, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "mcp_server"
        verbose_name = "MCP 服务器"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} [{self.transport}] {'ON' if self.enabled else 'OFF'}"


class McpTool(models.Model):
    """项目内自建 MCP 工具（Python 函数封装）。"""

    CATEGORY_CHOICES = [
        ("system", "系统运维"),
        ("database", "数据库"),
        ("network", "网络"),
        ("file", "文件"),
        ("custom", "自定义"),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="工具名称")
    description = models.CharField(max_length=500, verbose_name="工具描述")
    func_path = models.CharField(
        max_length=500, verbose_name="函数路径",
        help_text="Python 模块路径，如 tools.ssh_utils.ssh_exec"
    )
    parameters_schema = models.TextField(
        blank=True, default="",
        verbose_name="参数 Schema",
        help_text="JSON Schema 格式，描述参数"
    )
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="custom", verbose_name="分类"
    )
    enabled = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "mcp_tool"
        verbose_name = "MCP 工具"
        verbose_name_plural = verbose_name
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.category})"


class Skill(models.Model):
    """可配置的 Prompt 模板（Skill）。"""

    COLOR_CHOICES = [
        ("mint", "薄荷绿"),
        ("amber", "琥珀金"),
        ("blue", "蓝色"),
        ("purple", "紫色"),
        ("red", "红色"),
        ("pink", "粉色"),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="Skill 名称")
    description = models.CharField(max_length=500, verbose_name="描述")
    icon = models.CharField(
        max_length=50, default="sparkles",
        verbose_name="图标",
        help_text="Lucide 图标名，如 code, database, terminal, brain"
    )
    color = models.CharField(
        max_length=20, choices=COLOR_CHOICES, default="mint", verbose_name="主题色"
    )
    system_prompt = models.TextField(
        verbose_name="System Prompt 片段",
        help_text="激活后会追加到 AI 的 system prompt 中"
    )
    is_active = models.BooleanField(default=False, verbose_name="是否激活")
    created_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="skills", verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "skill"
        verbose_name = "Skill"
        verbose_name_plural = verbose_name
        ordering = ["-is_active", "-created_at"]

    def __str__(self):
        return f"{self.name} {'●' if self.is_active else '○'}"
