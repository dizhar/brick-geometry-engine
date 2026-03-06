from dotenv import load_dotenv
from crewai import Crew, Process
from src.agents import create_planner_agent, create_researcher_agent, create_writer_agent
from src.tasks import create_plan_task, create_research_task, create_write_task

# Load API key from .env
load_dotenv()

def run(user_request):
    # Create agents
    planner = create_planner_agent()
    researcher = create_researcher_agent()
    writer = create_writer_agent()

    # Create tasks
    plan_task = create_plan_task(planner, user_request)
    research_task = create_research_task(researcher, user_request)
    write_task = create_write_task(writer, user_request)

    # Assemble the crew
    crew = Crew(
        agents=[planner, researcher, writer],
        tasks=[plan_task, research_task, write_task],
        process=Process.sequential,
        verbose=True
    )

    result = crew.kickoff()
    print("\n========== FINAL OUTPUT ==========")
    print(result)

if __name__ == "__main__":
    run("""
    I am building BrickVisionAI - a LEGO computer vision system.
    I need a detailed project plan to build a LEGO Geometry Engine.
    
    The geometry engine needs to:
    1. Part metadata store - part ID, dimensions, category, mesh path
    2. Connector model - stud/anti-stud positions, types, normals
    3. Coordinate system - canonical system for all parts
    4. Connection rules engine - which connectors can mate
    5. Collision model - bounding box checks
    6. Pose/transform system - position and rotation of placed parts
    7. Assembly graph - nodes (parts) and edges (connections)
    
    Build in phases:
    - Phase A: common parts, stud/anti-stud only, box collisions, 90deg rotations
    - Phase B: slopes, technic connectors, better collisions
    - Phase C: hinges, axles, substitution logic, MOC generation
    
    Please:
    1. Create a detailed step by step build plan for Phase A only
    2. Define the folder structure for the project
    3. List which Python files to create and what each one does
    4. Suggest what to build first tomorrow morning
    """)