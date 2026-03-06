from crewai import Agent

def create_planner_agent():
    return Agent(
        role="Planner",
        goal="Break down complex tasks and delegate to the right specialist agents",
        backstory="You are a master planner who excels at analyzing tasks and routing them to the right experts.",
        verbose=True
    )

def create_researcher_agent():
    return Agent(
        role="Researcher",
        goal="Find and summarize relevant information on any given topic",
        backstory="You are an expert researcher who can quickly find and synthesize information.",
        verbose=True
    )

def create_writer_agent():
    return Agent(
        role="Writer",
        goal="Write clear, polished output based on research and instructions",
        backstory="You are a skilled writer who turns raw information into clear, structured content.",
        verbose=True
    )