import os
from typing import List, Optional, Tuple

from langchain.agents import Tool
from langchain_community.agent_toolkits import (
    FileManagementToolkit,
    PlayWrightBrowserToolkit,
)
from langchain_community.tools.arxiv.tool import ArxivQueryRun
from langchain_community.tools.wikipedia.tool import WikipediaQueryRun
from langchain_community.utilities import ArxivAPIWrapper, GoogleSerperAPIWrapper
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain_experimental.tools import PythonREPLTool
from playwright.async_api import async_playwright
from sympy import SympifyError, sympify


# Custom math tool
def safe_math_calculator(expression: str) -> str:
    """Safely evaluate mathematical expressions using sympy."""
    try:
        result = sympify(expression).evalf()
        return str(result)
    except (SympifyError, Exception) as e:
        return f"Error: Unable to evaluate expression '{expression}'. {str(e)}"


def create_search_tool() -> Optional[Tool]:
    """Create a web search tool"""
    try:
        serper = GoogleSerperAPIWrapper()
        return Tool(
            name="search",
            func=serper.run,
            description="Use this tool when you want to get the results of an online web search",
        )
    except Exception as e:
        print(f"Warning: Could not initialize search tool: {e}")
        return None


def create_math_tool() -> List[Tool]:
    """Create mathematical calculation tools."""
    return [
        Tool(
            name="calculator",
            func=safe_math_calculator,
            description="Use this tool when you want to do math, provide the expression as a string",
        )
    ]


def create_file_tools(root_dir: str = "sandbox") -> List[Tool]:
    """Create file management tools"""
    try:
        # Ensure the directory exists
        os.makedirs(root_dir, exist_ok=True)
        toolkit = FileManagementToolkit(root_dir=root_dir)
        return toolkit.get_tools()
    except Exception as e:
        print(f"Warning: Could not initialize file tools: {e}")
        return []


def create_wikipedia_tool() -> Optional[Tool]:
    """Create Wikipedia search tool"""
    try:
        wikipedia = WikipediaAPIWrapper()
        return WikipediaQueryRun(api_wrapper=wikipedia)
    except Exception as e:
        print(f"Warning: Could not initialize Wikipedia tool: {e}")
        return None


def create_arxiv_tool() -> Optional[Tool]:
    """Create ArXiv search tool"""
    try:
        return ArxivQueryRun(api_wrapper=ArxivAPIWrapper())
    except Exception as e:
        print(f"Warning: Could not initialize ArXiv tool: {e}")
        return None


def create_python_repl_tool() -> Optional[Tool]:
    """Create Python REPL tool"""
    try:
        return PythonREPLTool()
    except Exception as e:
        print(f"Warning: Could not initialize Python REPL tool: {e}")
        return None


async def create_playwright_tools() -> (
    Tuple[List[Tool], Optional[object], Optional[object]]
):
    """Create Playwright browser tools"""
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=browser)
        return toolkit.get_tools(), browser, playwright
    except Exception as e:
        print(f"Warning: Could not initialize Playwright tools: {e}")
        return [], None, None


def get_tools(sandbox_dir: str = "sandbox") -> List[Tool]:
    """
    Get all available tools.

    Args:
        sandbox_dir: Directory for file operations (default: "sandbox")

    Returns:
        List of initialized tools
    """
    tools = []

    # Add file management tools
    file_tools = create_file_tools(sandbox_dir)
    tools.extend(file_tools)

    # Add search tool
    search_tool = create_search_tool()
    if search_tool:
        tools.append(search_tool)

    # Add math tools
    math_tool = create_math_tool()
    tools.extend(math_tool)

    # Add Wikipedia tool
    wiki_tool = create_wikipedia_tool()
    if wiki_tool:
        tools.append(wiki_tool)

    # Add Python REPL tool
    python_tool = create_python_repl_tool()
    if python_tool:
        tools.append(python_tool)

    # Add ArXiv tool
    arxiv_tool = create_arxiv_tool()
    if arxiv_tool:
        tools.append(arxiv_tool)

    return tools


async def get_all_tools_with_browser(
    sandbox_dir: str = "sandbox",
) -> Tuple[List[Tool], Optional[object], Optional[object]]:
    """
    Get all tools including browser tools.

    Args:
        sandbox_dir: Directory for file operations (default: "sandbox")

    Returns:
        Tuple of (tools_list, browser_instance, playwright_instance)
    """
    # Get basic tools
    tools = get_tools(sandbox_dir)

    # Add browser tools
    browser_tools, browser, playwright = await create_playwright_tools()
    tools.extend(browser_tools)

    return tools, browser, playwright
