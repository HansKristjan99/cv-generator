from getpass import getpass
import os
from langchain_protocol import Annotated
from langchain.messages import AnyMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from pydantic import BaseModel, Field
from typing_extensions import TypedDict, Annotated
from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI
import operator

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass(f"{var}: ")


_set_env("OPENAI_API_KEY")



class JobRequirement(BaseModel):
    """One distinct job requirement, classified and checked against the candidate."""

    requirement: str = Field(
        ..., description="A single distinct requirement, tightly paraphrased from the job description."
    )
    importance: str = Field(
        ...,
        description=(
            "'must_have' if the posting frames it as required/essential/minimum; "
            "'nice_to_have' for preferred, bonus, or 'a plus' items."
        ),
    )
    met: bool = Field(
        ...,
        description=(
            "True only if the candidate's source material or stored profile already "
            "provides credible evidence for this requirement."
        ),
    )
    evidence: str = Field(
        ...,
        description=(
            "The specific candidate fact that satisfies it (role, project, skill, "
            "education), or the literal string 'Not satisfied'."
        ),
    )
    question: str = Field(
        ...,
        description=(
            "If not met, ONE targeted question asking the candidate for the specific "
            "missing evidence. Empty string when the requirement is met."
        ),
    )


class RequirementsAnalysis(BaseModel):
    """The full per-requirement analysis for a job description."""

    requirements: list[JobRequirement] = Field(
        ..., description="One entry per distinct requirement in the job description."
    )


class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    input: Annotated[str, operator.add]
    requirements_analysis: Annotated[RequirementsAnalysis, operator.add]
    hiring_manager_feedback: Annotated[str, operator.add]
    llm_calls: int



def extract_requirements_analysis(state: MessagesState) -> MessagesState:
    input = state["input"]

    llm = ChatOpenAI(model = "gpt-5.4-mini")
    analysis = llm.with_structured_output(RequirementsAnalysis).invoke(input)
    print("Extracted requirements analysis:", analysis)
    return {
        **state,
        "requirements_analysis": analysis,
    }

graph = StateGraph(MessagesState)
graph.add_node(extract_requirements_analysis)
graph.add_edge(START, "extract_requirements_analysis")
graph.add_edge("extract_requirements_analysis", END)
graph = graph.compile()

graph.invoke({"input": "hi!"})