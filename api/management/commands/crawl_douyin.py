"""管理命令：爬取抖音热搜并入库"""

from django.core.management.base import BaseCommand

from api.crawler import fetch_and_save


class Command(BaseCommand):
    help = "爬取抖音热搜榜数据并保存到数据库"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("开始爬取抖音热搜..."))

        result = fetch_and_save()

        self.stdout.write(
            self.style.SUCCESS(
                f"爬取完成！共保存 {result['total']} 条数据，"
                f"批次时间: {result['batch_time']}"
            )
        )

        # 打印前 5 条
        self.stdout.write("\n前 5 条热搜：")
        for item in result["items"][:5]:
            self.stdout.write(
                f"  #{item['rank']}  {item['title']}  "
                f"热度: {item['hot_value']:,}  标签: {item['label']}"
            )
