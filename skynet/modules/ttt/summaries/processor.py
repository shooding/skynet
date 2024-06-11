from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import ChatPromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from skynet.env import app_uuid, llama_n_ctx, openai_api_base_url
from skynet.logs import get_logger

from .prompts.action_items import action_items_conversation_prompt, action_items_text_prompt
from .prompts.summary import summary_conversation_prompt, summary_text_prompt
from .v1.models import DocumentPayload, HintType, JobType

llm = None
log = get_logger(__name__)


hint_type_to_prompt = {
    JobType.SUMMARY: {
        HintType.CONVERSATION: summary_conversation_prompt,
        HintType.TEXT: summary_text_prompt,
    },
    JobType.ACTION_ITEMS: {
        HintType.CONVERSATION: action_items_conversation_prompt,
        HintType.TEXT: action_items_text_prompt,
    },
}


def initialize():
    global llm

    llm = ChatOpenAI(
        api_key='placeholder',  # use a placeholder value to bypass validation, and allow the custom base url to be used
        base_url=openai_api_base_url,
        default_headers={"X-Skynet-UUID": app_uuid},
        max_retries=0,
        temperature=0,
    )


async def process(payload: DocumentPayload, job_type: JobType, model: ChatOpenAI = None) -> str:
    current_model = model or llm
    chain = None
    text = payload.text

    if not text:
        return ""

    system_message = hint_type_to_prompt[job_type][payload.hint]
    prompt = ChatPromptTemplate.from_messages([("system", system_message), ("user", "{text}")])

    # this is a rough estimate of the number of tokens in the input text, since llama models will have a different tokenization scheme
    num_tokens = current_model.get_num_tokens(text)

    # allow some buffer for the model to generate the output
    threshold = llama_n_ctx * 3 / 4

    if num_tokens < threshold:
        chain = load_summarize_chain(current_model, chain_type="stuff", prompt=prompt)
        docs = [Document(page_content=text)]
    else:
        # split the text into roughly equal chunks
        num_chunks = num_tokens // threshold + 1
        chunk_size = num_tokens // num_chunks

        log.info(f"Splitting text into {num_chunks} chunks of {chunk_size} tokens")

        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=chunk_size, chunk_overlap=100)
        docs = text_splitter.create_documents([text])
        chain = load_summarize_chain(current_model, chain_type="map_reduce", combine_prompt=prompt, map_prompt=prompt)

    result = await chain.ainvoke(input={"input_documents": docs})

    return result['output_text'].strip()


async def process_open_ai(payload: DocumentPayload, job_type: JobType, api_key: str, model_name=None) -> str:
    llm = ChatOpenAI(
        api_key=api_key,
        model_name=model_name,
        temperature=0,
    )

    return await process(payload, job_type, llm)
