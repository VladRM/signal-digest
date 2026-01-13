from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
# from langchain_community.document_loaders import YoutubeLoader # If using transcript method

# 1. Define the graph state
class GraphState:
    def __init__(self, youtube_url: str = "", summary: str = ""):
        self.youtube_url = youtube_url
        self.summary = summary

# 2. Define the nodes (functions)
def call_gemini_node(state: GraphState):
    """Processes the video URL with Gemini 3 Flash."""
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash") # Specify the model
    
    # Pass the URL directly to the model as a multimodal part
    message = HumanMessage(
        content=[
            {"type": "text", "text": "Please provide a detailed summary and key insights of this YouTube video."},
            {"type": "video", "base64": None, "mime_type": "video/mp4", "uri": state.youtube_url} # Use uri for URL
        ]
    )
    
    response = model.invoke([message])
    return GraphState(summary=response.content, youtube_url=state.youtube_url)

# 3. Build the graph
workflow = StateGraph(GraphState)

workflow.add_node("process_video", call_gemini_node)

workflow.add_edge("process_video", END)

# Set the entry point
workflow.set_entry_point("process_video")

# Compile the graph
app = workflow.compile()


inputs = GraphState(youtube_url="https://www.youtube.com/watch?v=QvgEyCasIKI")

for output in app.stream(inputs):
    # Stream the output
    for key, value in output.items():
        print(f"Output from Node '{key}': {value}")