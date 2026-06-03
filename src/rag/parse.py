import os
from dotenv import load_dotenv
# from markitdown import MarkItDown
# from openai import OpenAI
from docling.document_converter import DocumentConverter

load_dotenv()

source = "/home/asd841018/mini-agent/.assets/91ba1d46cdde9c1c0cf34f6bcc107741244f8f3d.pdf"
converter = DocumentConverter()
result = converter.convert(source)
print(result.document.export_to_markdown())
# md = MarkItDown(
#     enable_plugins=True,
#     llm_client=OpenAI(
#         api_key=os.environ.get("OPENAI_API_KEY"),
#     ),
#     llm_model="gpt-4o",
# )

# result = md.convert("/home/asd841018/mini-agent/.assets/91ba1d46cdde9c1c0cf34f6bcc107741244f8f3d.pdf")
# with open("output.md", "w", encoding="utf-8") as file:
    # file.write(result.text_content)
# result.save_as_markdown("./test.md")
# result.markdown