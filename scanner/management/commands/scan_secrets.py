"""管理命令：扫描硬编码密钥（支持指定其他代码仓）"""

from django.conf import settings
from django.core.management.base import BaseCommand

from tools.secret_scanner import ScanTimeoutError, scan_target


class Command(BaseCommand):
    help = "扫描项目代码中的硬编码密钥（Web 扫描功能的管理命令版）"

    def add_arguments(self, parser):
        parser.add_argument(
            "target", nargs="?", default="",
            help="扫描目标：留空=当前项目；本地绝对路径；Git 仓库 URL（https://...git）",
        )

    def handle(self, *args, **options):
        target = options.get("target") or ""
        self.stdout.write(
            self.style.WARNING(f"开始扫描硬编码密钥（目标: {target or '当前项目'}）...")
        )
        try:
            result = scan_target(
                target, str(settings.BASE_DIR),
                max_seconds=120, max_files=20000,
            )
        except ScanTimeoutError as e:
            self.stderr.write(self.style.ERROR(f"扫描中止：{e}"))
            raise SystemExit(1)

        self.stdout.write(
            self.style.SUCCESS(
                f"扫描完成：{result['files_scanned']} 个文件，发现 {len(result['findings'])} 处"
            )
        )
        for f in result["findings"]:
            self.stdout.write(
                f"  [{f['severity']}] {f['rule_name']}: "
                f"{f['file_path']}:{f['line_number']} "
                f"(熵 {f['entropy']}, 密钥 {f['secret_preview']})"
            )
