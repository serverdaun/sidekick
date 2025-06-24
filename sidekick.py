import asyncio
import uuid
from datetime import datetime
from typing import Annotated, Any, List, Literal, Optional

from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from config import OPENAI_CHAT_MODEL_EVALUATOR, OPENAI_CHAT_MODEL_WORKER
from tools import get_all_tools_with_browser


class State(BaseModel):
    """State for the Sidekick"""

    messages: Annotated[List[Any], add_messages]
    success_criteria: str
    feedback_on_work: Optional[str]
    success_criteria_met: bool
    user_input_needed: bool


class EvaluatorOutput(BaseModel):
    """Output for the evaluator"""

    feedback: str = Field(description="Feedback on the assistant's response")
    success_criteria_met: bool = Field(
        description="Whether the success criteria have been met"
    )
    user_input_needed: bool = Field(
        description="True if more input is needed from the user, or clarifications, or the assistant is stuck"
    )


class Sidekick:
    """Sidekick class"""

    def __init__(self, memory_file: str = "sidekick_memory.json"):
        """Initialize the Sidekick"""

        self.worker_llm_with_tools = None
        self.evaluator_llm_with_output = None
        self.tools = None
        self.llm_with_tools = None
        self.graph = None
        self.sidekick_id = str(uuid.uuid4())
        self.memory = MemorySaver()
        self.browser = None
        self.playwright = None
        self.chat_memory = FileChatMessageHistory(file_path=memory_file)

    async def setup(self) -> None:
        """Setup function"""

        self.tools, self.browser, self.playwright = await get_all_tools_with_browser()
        worker_llm = ChatOpenAI(model=OPENAI_CHAT_MODEL_WORKER)
        self.worker_llm_with_tools = worker_llm.bind_tools(self.tools)

        evaluator_llm = ChatOpenAI(model=OPENAI_CHAT_MODEL_EVALUATOR)
        self.evaluator_llm_with_output = evaluator_llm.with_structured_output(
            EvaluatorOutput
        )
        await self.build_graph()

    async def worker(self, state: State) -> State:
        """Worker function"""

        system_message = f"""You are a helpful assistant that can use tools to complete tasks.
    You keep working on a task until either you have a question or clarification for the user, or the success criteria is met.
    You have many tools to help you, including tools to browse the internet, navigating and retrieving web pages.
    You have a tool to run python code, but note that you would need to include a print() statement if you wanted to receive output.
    The current date and time is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    This is the success criteria:
    {state.success_criteria}
    You should reply either with a question for the user about this assignment, or with your final response.
    If you have a question for the user, you need to reply by clearly stating your question. An example might be:

    Question: please clarify whether you want a summary or a detailed answer

    If you've finished, reply with the final answer, and don't ask a question; simply reply with the answer.
    """

        if state.feedback_on_work:
            system_message += f"""
    Previously you thought you completed the assignment, but your reply was rejected because the success criteria was not met.
    Here is the feedback on why this was rejected:
    {state.feedback_on_work}
    With this feedback, please continue the assignment, ensuring that you meet the success criteria or have a question for the user."""

        # Add in the system message
        found_system_message = False
        messages = state.messages
        for message in messages:
            if isinstance(message, SystemMessage):
                message.content = system_message
                found_system_message = True

        if not found_system_message:
            messages = [SystemMessage(content=system_message)] + messages

        # Invoke the LLM with tools (async)
        response = await self.worker_llm_with_tools.ainvoke(messages)

        # Return updated state
        return {
            "messages": [response],
        }

    def worker_router(self, state: State) -> Literal["tools", "evaluator"]:
        """Worker router function"""

        last_message = state.messages[-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        else:
            return "evaluator"

    def format_conversation(self, messages: List[Any]) -> str:
        """Format conversation function"""

        conversation = "Conversation history:\n\n"
        for message in messages:
            if isinstance(message, HumanMessage):
                conversation += f"User: {message.content}\n"
            elif isinstance(message, AIMessage):
                text = message.content or "[Tools use]"
                conversation += f"Assistant: {text}\n"
        return conversation

    async def evaluator(self, state: State) -> State:
        """Evaluator function"""

        last_response = state.messages[-1].content

        system_message = f"""You are an evaluator that determines if a task has been completed successfully by an Assistant.
    Assess the Assistant's last response based on the given criteria. Respond with your feedback, and with your decision on whether the success criteria has been met,
    and whether more input is needed from the user."""

        user_message = f"""You are evaluating a conversation between the User and Assistant. You decide what action to take based on the last response from the Assistant.

    The entire conversation with the assistant, with the user's original request and all replies, is:
    {self.format_conversation(state.messages)}

    The success criteria for this assignment is:
    {state.success_criteria}

    And the final response from the Assistant that you are evaluating is:
    {last_response}

    Respond with your feedback, and decide if the success criteria is met by this response.
    Also, decide if more user input is required, either because the assistant has a question, needs clarification, or seems to be stuck and unable to answer without help.

    The Assistant has access to a tool to write files. If the Assistant says they have written a file, then you can assume they have done so.
    Overall you should give the Assistant the benefit of the doubt if they say they've done something. But you should reject if you feel that more work should go into this.

    """
        if state.feedback_on_work:
            user_message += f"""Also, note that in a prior attempt from the Assistant, you provided this feedback: {state.feedback_on_work}

If you're seeing the Assistant repeating the same mistakes, then consider responding that user input is required."""

        evaluator_messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=user_message),
        ]

        eval_result = await self.evaluator_llm_with_output.ainvoke(evaluator_messages)
        new_state = {
            "messages": [
                AIMessage(
                    content=f"Evaluator Feedback on this answer: {eval_result.feedback}"
                )
            ],
            "feedback_on_work": eval_result.feedback,
            "success_criteria_met": eval_result.success_criteria_met,
            "user_input_needed": eval_result.user_input_needed,
        }
        return new_state

    def route_based_on_evaluation(self, state: State) -> Literal["worker", "END"]:
        """Route based on evaluation function"""

        if state.success_criteria_met or state.user_input_needed:
            return "END"
        else:
            return "worker"

    async def build_graph(self) -> None:
        """Build the graph"""

        # Set up Graph Builder with State
        graph_builder = StateGraph(State)

        # Add nodes
        graph_builder.add_node("worker", self.worker)
        graph_builder.add_node("tools", ToolNode(tools=self.tools))
        graph_builder.add_node("evaluator", self.evaluator)

        # Add edges
        graph_builder.add_conditional_edges(
            "worker", self.worker_router, {"tools": "tools", "evaluator": "evaluator"}
        )
        graph_builder.add_edge("tools", "worker")
        graph_builder.add_conditional_edges(
            "evaluator",
            self.route_based_on_evaluation,
            {"worker": "worker", "END": END},
        )
        graph_builder.add_edge(START, "worker")

        # Compile the graph
        self.graph = graph_builder.compile(checkpointer=self.memory)

    async def run_superstep(
        self, message: str, success_criteria: str, history: List[Any]
    ) -> List[Any]:
        """Run a superstep"""

        config = {"configurable": {"thread_id": self.sidekick_id}}

        # Load persistent conversation history.
        persistent_messages = self.chat_memory.messages if self.chat_memory else []

        # Build the initial state for the graph including persistent history and the new user message.
        state = {
            "messages": persistent_messages + [HumanMessage(content=message)],
            "success_criteria": success_criteria
            or "The answer should be clear and accurate",
            "feedback_on_work": None,
            "success_criteria_met": False,
            "user_input_needed": False,
        }
        result = await self.graph.ainvoke(state, config=config)

        # Update the persistent memory with the new user and assistant messages
        self.chat_memory.add_user_message(message)

        # The assistant's reply is the second to last message (the last one is evaluator feedback)
        assistant_reply_content = result["messages"][-2].content
        self.chat_memory.add_ai_message(assistant_reply_content)

        user = {"role": "user", "content": message}
        reply = {"role": "assistant", "content": assistant_reply_content}
        feedback = {"role": "assistant", "content": result["messages"][-1].content}
        return history + [user, reply, feedback]

    def cleanup(self) -> None:
        """Cleanup function"""

        if self.browser:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.browser.close())
                if self.playwright:
                    loop.create_task(self.playwright.stop())
            except RuntimeError:
                # If no loop is running, do a direct run
                asyncio.run(self.browser.close())
                if self.playwright:
                    asyncio.run(self.playwright.stop())

    def free_resources(self) -> None:
        """Public alias for cleanup so external callers can reliably release resources."""
        self.cleanup()
