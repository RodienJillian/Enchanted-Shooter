from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from game_manager import game_manager

app = FastAPI(title="Taylor Swift Lyric Guesser API", version="1.0.0")

# Add CORS middleware - connection to svelte
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GameQuestion(BaseModel):
    incomplete_lyric: str
    correct_answer: str
    options: List[str]
    question_id: str

class GameAnswer(BaseModel):
    session_id: str
    selected_answer: str

class GameStats(BaseModel):
    vocabulary_size: int
    ngram_count: int
    total_ngrams: int

class SessionStats(BaseModel):
    score: int
    questions_answered: int
    accuracy: float

@app.get("/")
async def root():
    return {"message": "Taylor Swift Lyric Guesser API"}

@app.get("/health")
async def health_check():
    try:
        stats = game_manager.get_model_stats()
        return {"status": "healthy", "model_loaded": True, "vocabulary_size": stats["vocabulary_size"]}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Game model not available: {str(e)}")

@app.get("/stats", response_model=GameStats)
async def get_stats():
    try:
        stats = game_manager.get_model_stats()
        return GameStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

@app.post("/session")
async def create_session():
    """Create a new game session."""
    try:
        session_id = game_manager.create_session()
        return {"session_id": session_id, "message": "Session created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")

@app.get("/question/{session_id}", response_model=GameQuestion)
async def get_question(session_id: str, song: str | None = Query(default=None), part: str | None = Query(default=None)):
    """Get a new question for the given session.
    Optional query params:
    - song: song title to constrain the question
    - part: difficulty or song part (easy->Chorus, medium->Verse, hard/difficult->Bridge)
    """
    try:
        question = game_manager.get_question(session_id, song=song, part=part)
        if not question:
            raise HTTPException(status_code=404, detail="Session not found or could not generate question")
        
        return GameQuestion(**question)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating question: {str(e)}")

@app.get("/songs")
async def list_songs():
    """List available songs with album and parts."""
    try:
        songs = game_manager.list_songs()
        return {"songs": songs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing songs: {str(e)}")

@app.post("/check-answer")
async def check_answer(answer: GameAnswer):
    """Check if the selected answer is correct for the current session question."""
    try:
        result = game_manager.check_answer(answer.session_id, answer.selected_answer)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking answer: {str(e)}")

@app.get("/session/{session_id}/stats", response_model=SessionStats)
async def get_session_stats(session_id: str):
    """Get statistics for a specific session."""
    try:
        stats = game_manager.get_session_stats(session_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionStats(**stats)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting session stats: {str(e)}")

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a game session."""
    try:
        success = game_manager.cleanup_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": "Session deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
