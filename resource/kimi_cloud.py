# encoding=utf-8
import base64
import json
import re
from pathlib import Path
from openai import OpenAI
from pdf2image import convert_from_path
from io import BytesIO


class PdfParser:
    def __init__(self, api_key, base_url, model="kimi-k2.5"):
        # self.pdf_path = pdf_path
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        self.img_base64 = ""
        # file_object = self.client.files.create(
        #     file=Path(self.pdf_path),
        #     purpose="file-extract",
        # )
        # self.file_content = self.client.files.content(file_id=file_object.id).text

    def parse(self, pdf_path: str):
        print(f"[DEBUG] 开始解析PDF: {pdf_path}")
        try:
            pages = convert_from_path(pdf_path, poppler_path=r'D:\poppler-25.12.0\Library\bin')
            print(f"[DEBUG] PDF页数: {len(pages)}")
            img_buffer = BytesIO()
            pages[0].save(img_buffer, format="PNG")
            self.img_base64 = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
            print(f"[DEBUG] 图片base64长度: {len(self.img_base64)}")
        except Exception as e:
            print(f"[ERROR] PDF转换图片失败: {pdf_path}, 错误: {e}")
            import traceback

            traceback.print_exc()
            return None

        print(f"[DEBUG] 开始API调用...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "电子报内容识别"},
                    {
                        "role": "system",
                        "content": """
                    返回的json格式应严格为如下形式：{
                        "success": true,
                        "errMsg": "识别成功",
                        "data": [
                            {
                                "page_no": "1",
                                "page_name": "海山观察",
                                "title": "文章标题",
                                "author": "作者",
                                "collaborator": "通讯员",
                                "photo": "摄影",
                                "content": "内容",
                                "has_previous": false,
                                "is_xinhua": 0,
                                "is_pic": 0,
                                "next_page": "",
                                "hot_zone": [[300, 100], [300, 200], [400, 200], [400, 100]]
                            }
                        ]
                    }
                """,
                    },
                    # {"role": "system", "content": self.file_content},
                    # {"role": "user", "content": f"请将对电子报中的文章内容进行提取，以json列表的形式返回出来，例表内的对象包括文章名、作者、摄像、内容、页面版号等"},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{self.img_base64}"
                                },
                            },
                            {
                                "type": "text",
                                "text": "请完整且准确地识别电子报中的文章的内容和标点符号，以json列表的形式返回出来，例表内的对象包括文章名、作者、通讯员、摄影、内容、热区、所在版面号和版面名等",
                            },
                        ],
                    },
                    {"role": "assistant", "content": "干览镇应改为干𬒗镇"},
                    {
                        "role": "assistant",
                        "content": "副标题应放到标题后，不应噶出现在内容前端",
                    },
                    {
                        "role": "assistant",
                        "content": "严格按照文章文字，不要添加任何解释或说明",
                    },
                    {
                        "role": "assistant",
                        "content": "专题页面的稿子，在一个大题目下包含了多个并列类似结构形式题目的子文章，请将他们合并为一篇文章",
                    },
                    {
                        "role": "assistant",
                        "content": "注意对内容的分段处理，每个段落之间用换行符隔开",
                    },
                    {
                        "role": "assistant",
                        "content": "如文章末尾有“下紧转第x版”的，在返回的json中，next_page字段填写下一页的版面号，且content中不包含“下紧转第x版”",
                    },
                    # {
                    #     "role": "assistant",
                    #     "content": "去掉内容开头“上紧接第x版”这类字符，如有该字符串则has_previouse为true"
                    # },
                    {
                        "role": "assistant",
                        "content": "如果文章以“上紧接第x版”这类字符开头的，如无法确定标题则空着，内容去掉“上紧接第x版”这类字符，has_previous设置为true",
                    },
                    {
                        "role": "assistant",
                        "content": "版面名为“海山观察”的文章，作者应被认为是通讯员",
                    },
                    {
                        "role": "assistant",
                        "content": "版面名为“海潮文艺”的文章，作者应被认为是通讯员",
                    },
                    {
                        "role": "assistant",
                        "content": "版面名为“舟山警擦”的文章，作者、摄影应被认为是通讯员",
                    },
                    {
                        "role": "assistant",
                        "content": "版面名为“海潮理论”的文章，有明确记者标记的作者为记者，否则该作者应被认为是通讯员",
                    },
                    {
                        "role": "assistant",
                        "content": "版面名为“海潮人文”的文章，有明确记者标记的作者为记者，否则该作者应被认为是通讯员",
                    },
                    {
                        "role": "assistant",
                        "content": "在文章开头处括号内的有明显记者标记的作者，应被认为是记者",
                    },
                    {
                        "role": "assistant",
                        "content": "“新华社”不属于作者、通讯员、摄影等字段",
                    },
                    {
                        "role": "assistant",
                        "content": "如文章开头或者结尾有类似“新华社纽约3月1日电”的字符串，请保留并设置is_xinhua字段为1，否则设置为0",
                    },
                    {
                        "role": "assistant",
                        "content": "如文章开头或者结尾有类似“新华社 发”的字符串，请保留并设置is_xinhua字段为1，否则设置为0",
                    },
                    {"role": "assistant", "content": "“本报评论员”不属于作者"},
                    {
                        "role": "assistant",
                        "content": "页面版本号一般在整个页面的顶部或者四周边，明显的数字或者字母加数字的字符串；页面版面名一般在页面的顶部或者四周边，明显的文字字符串，表示这个版面的内容性质；版面号为1时，版面名统一为“头版”；有时候“海潮”开头的版面名中的文字存在不同格式，注意合并处理；如无法获取版面名，则写为“第x版面”",
                    },
                    {
                        "role": "assistant",
                        "content": "热区一般是页面的某个区域，表示当前整篇文章在页面中占据的矩形区域，热区的坐标一般是矩形的四个角在页面x、y轴上的像素坐标，例如[[300, 100], [300, 200], [400, 200], [400, 100]]",
                    },
                    {
                        "role": "assistant",
                        "content": "记者、通讯员、摄影等字符串，在相应的字段里要去掉，也就是说记者字段里不能包含“记者”这个字符串，且多个人之间用空格隔开",
                    },
                    {
                        "role": "assistant",
                        "content": "内容和标题里的引号都替换为中文引号",
                    },
                    {
                        "role": "assistant",
                        "content": "没有作者的文章，内容较少但有图片的，如标题难以获取，将内容作为标题",
                    },
                    {
                        "role": "assistant",
                        "content": "如摄影、通讯员同时标注时，则为通讯员",
                    },
                    {
                        "role": "assistant",
                        "content": "如果文章范围内，有“海山时评”的图标，在题目开头前添加“海山时评”，且该作者务必应为通讯员",
                    },
                    {
                        "role": "assistant",
                        "content": "图片的热区矩形范围与文章热区矩形范围有交集，且图片的热区矩形范围与文章热区矩形范围的面积比例大于0.6，则将该文章的is_pic设置为1，否则设置为0",
                    },
                    # {
                    #     "role": "assistant",
                    #     "content": "图片列表是文章热区矩形范围内包含的图片，每个图片都是png格式的base64编码"
                    # }
                ],
                response_format={"type": "json_object"},
                stream=False,
            )
        except Exception as e:
            print(f"API调用失败: {pdf_path}, 错误: {e}")
            return None
        # print(response)
        ret_str = response.choices[0].message.content
        if ret_str.startswith("```json"):
            ret_str = ret_str[7:]
        if ret_str.endswith("```"):
            ret_str = ret_str[:-3]
        ret_str = ret_str.strip()
        print(f"[DEBUG] API返回内容长度: {len(ret_str)}")

        # 检查是否返回 high risk
        if "high risk" in ret_str.lower() or "risk" in ret_str.lower():
            print(f"[WARNING] Kimi返回 high risk: {pdf_path}")
            return {
                "high_risk": True,
                "success": False,
                "errMsg": "high risk",
                "data": [],
            }

        print(ret_str)
        try:
            ret = json.loads(ret_str)
            print(f"[DEBUG] JSON解析成功，文章数: {len(ret.get('data', []))}")
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON解析失败: {pdf_path}, 错误: {e}")
            print(f"[ERROR] 返回内容: {ret_str[:500]}")
            return None
        # ret["pdf"] = pdf_path
        return ret


class PdfParserNext:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def any_next(self, ret, next_pages):
        if ret["success"]:
            for ra in ret["data"]:
                if len(ra["next_page"]) > 0:
                    for p in next_pages:
                        parser = PdfParser(p, api_key)
                        ret_2 = parser.parse()
                        if ret_2["success"]:
                            for a in ret_2["data"]:
                                if a["title"] in ra["title"]:
                                    ra["content"] += a["content"]
                                    if ra["author"] == "" and a["author"]:
                                        ra["author"] = a["author"]
                                    if ra["collaborator"] == "" and a["collaborator"]:
                                        ra["collaborator"] = a["collaborator"]
                                    if ra["photo"] == "" and a["photo"]:
                                        ra["photo"] = a["photo"]
        return ret


if __name__ == "__main__":
    # moonshot cloud
    # api_key = "sk-BSvteGexprXexqyk6O5RBSPJtcmBNzoZwHVnVAAmJTUPIZTE"
    # base_url = "https://api.moonshot.cn/v1"
    # model = "kimi-k2.5"
    # api_key = "ollama-local"
    # base_url = "http://localhost:11434/v1"
    # model = "qcwind/qwen3-vl-8b-q4_k_m"
    # model = "qwen3-vl:8b-instruct"
    # alibaba cloud
    api_key = "sk-e2cdbb4075d841d0a199cd4c7378a1cc"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    # model = "qwen2.5-omni-7b"
    model = "qwen3.5-plus"
    for pdf_path in [
        # "special/B2026-01-28_01.pdf",
        # "special/B2026-03-10六版01.pdf",
        # "special/2026030906.pdf",
        # "舟山日报/20260304PDF/B2026-03-04三版01.pdf",
        # "舟山日报/20260305PDF/2026-03-05五版01.FIT).pdf"
        # "舟山日报/20260305PDF/B2026-03-05一版01.pdf"
        # "舟山日报/z20260309pdf/z030901.pdf"
        # "舟山日报/Z20260310PDF/B2026-03-10二版01.pdf"
        "舟山日报/z20260315pdf/z031501.pdf"
    ]:
        # pdf_path = "special/B2026-01-28_01.pdf"

        # pdf_path = "special/b2026-01-25_01.pdf"
        parser = PdfParser(api_key, base_url, model)
        ret = parser.parse(pdf_path)

        # pn = PdfParserNext(api_key, base_url, model)
        # ret = pn.any_next(ret, ["special/b2026-01-25_04.pdf"])
        # print(ret)
