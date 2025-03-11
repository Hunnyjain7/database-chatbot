import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.question_handler import handle_question

router = APIRouter()

async def handle_run_query(websocket: WebSocket, message_id: str, query: str, user: str, password: str, host: str, database: str):
    try:
        if query:
            result = handle_question(query, user, password, host, database)
            response = [message_id, "answer_query", result]
        else:
            response = [message_id, "answer_query", {"status": 0, "data": None, "message": "No query provided"}]
    except Exception as e:
        response = [message_id, "answer_query", {"status": 0, "data": None, "message": str(e)}]

    try:
        await websocket.send_json(response)
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Unexpected error sending response: {e}")

async def handle_message(websocket: WebSocket, message: str):
    try:
        message_id, action, data = json.loads(message)
        if action == "run_query":
            query_data = data.get("query", {})
            query = query_data.get("query")
            user = query_data.get("user")
            password = query_data.get("password")
            host = query_data.get("host")
            database = query_data.get("database")
            await handle_run_query(websocket, message_id, query, user, password, host, database)
        else:
            response = [message_id, "answer_query", {"status": 0, "data": None, "message": f"Unknown action: {action}"}]
            await websocket.send_json(response)
    except json.JSONDecodeError:
        response = [0, "answer_query", {"status": 0, "data": None, "message": "Invalid JSON format"}]
        await websocket.send_json(response)
    except ValueError as e:
        response = [0, "answer_query", {"status": 0, "data": None, "message": str(e)}]
        await websocket.send_json(response)
    except Exception as e:
        response = [0, "answer_query", {"status": 0, "data": None, "message": str(e)}]
        await websocket.send_json(response)

@router.websocket("/askQuestion")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        async for message in websocket.iter_text():
            await handle_message(websocket, message)
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Unexpected error: {e}")
