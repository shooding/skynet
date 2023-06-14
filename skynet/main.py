from fastapi import FastAPI
from fastapi_versionizer.versionizer import api_version, versionize

from skynet.langchain import Langchain
from skynet.models.summary import SummaryPayload

app = FastAPI()
langchain = Langchain()

@api_version(1)
@app.post("/summarize")
def summarize(payload: SummaryPayload):
    return langchain.summarize(payload)

@app.get("/summary/{id}")
def get_summary(id: str, retrieveActionItems: bool = False):
    return langchain.get_summary(id, retrieveActionItems)

@app.put("/summary/{id}")
def update_summary(id: str, payload: SummaryPayload):
    return langchain.update_summary(id, payload)

@app.delete("/summary/{id}")
def delete_summary(id: str):
    return langchain.delete_summary(id)

versions = versionize(
    app=app,
    prefix_format='/v{major}',
    docs_url='/docs',
    enable_latest=True,
    latest_prefix='/latest',
    sorted_routes=True
)