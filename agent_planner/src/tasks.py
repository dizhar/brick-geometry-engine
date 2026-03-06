from crewai import Task

def create_research_task(agent, topic):
    return Task(
        description=f"Research the following topic and summarize key findings: {topic}",
        expected_output="A clear, concise summary of the most important information on the topic.",
        agent=agent
    )

def create_write_task(agent, research_output):
    return Task(
        description=f"Using this research: {research_output}. Write a clear, structured report.",
        expected_output="A well-written, polished report based on the research provided.",
        agent=agent
    )

def create_plan_task(agent, user_request):
    return Task(
        description=f"Break down this request into clear steps: {user_request}",
        expected_output="A structured plan with clear steps to accomplish the requested task.",
        agent=agent
    )