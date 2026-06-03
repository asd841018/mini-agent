import os
from dotenv import load_dotenv
from markitdown import MarkItDown
from openai import OpenAI


load_dotenv()

md = MarkItDown(
    enable_plugins=True,
    llm_client=OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
    ),
    llm_model="gpt-4o",
)

result = md.convert("/Users/jerry/Downloads/pdf_reports/91ba1d46cdde9c1c0cf34f6bcc107741244f8f3d.pdf")
with open("output.md", "w", encoding="utf-8") as file:
    file.write(result.text_content)
# result.save_as_markdown("./test.md")
# result.markdown