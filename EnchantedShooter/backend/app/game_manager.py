import random
import uuid
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from ngram_model import NGramModel

class GameSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_question: Optional[Dict] = None
        self.score = 100
        self.questions_answered = 0
        self.created_at = None
        # ordered playback state
        self.song_title: Optional[str] = None
        self.song_part: Optional[str] = None
        self.part_lines_ordered: List[Dict] = []
        self.part_index: int = 0

class GameManager:
    def __init__(self):
        self.ngram_model = NGramModel()
        self.sessions: Dict[str, GameSession] = {}
        # Load structured lyrics for song/part selection
        self.song_data = self._load_raw_lyrics()
        self.songs_index_by_title = self._index_songs_by_title(self.song_data)
        self.song_parts_by_title = self._collect_song_parts(self.song_data)
    
    def create_session(self) -> str:
        """Create a new game session and return the session ID."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = GameSession(session_id)
        return session_id
    
    def get_question(self, session_id: str, song: Optional[str] = None, part: Optional[str] = None) -> Optional[Dict]:
        """Get a new question for the given session.
        If song and part are provided, attempt to generate a question from that specific song section.
        """
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]

        # Try song/part filtered question if provided
        filtered_question: Optional[Dict] = None
        if song and part:
            # Setup or continue ordered list
            filtered_question = self._generate_ordered_question(session, song, part)

        if not filtered_question:
            # Fallback to model-generated question
            incomplete_line, correct_word, distractors = self.ngram_model.generate_incomplete_lyric()
            if not incomplete_line or not correct_word or not distractors:
                return None
            options = [correct_word] + distractors
            random.shuffle(options)
            question = {
                "incomplete_lyric": incomplete_line,
                "correct_answer": correct_word,
                "options": options,
                "question_id": f"q_{random.randint(10000, 99999)}"
            }
        else:
            question = filtered_question

        session.current_question = question
        return session.current_question
    
    def check_answer(self, session_id: str, selected_answer: str) -> Dict:
        """Check if the selected answer is correct for the current session question."""
        if session_id not in self.sessions:
            return {"error": "Invalid session"}
        
        session = self.sessions[session_id]
        
        if not session.current_question:
            return {"error": "No current question"}
        
        correct_answer = session.current_question["correct_answer"]
        is_correct = selected_answer.lower() == correct_answer.lower()
        
        session.questions_answered += 1
        if not is_correct:
            # subtract 10 points per wrong answer, floor at 0
            session.score = max(0, session.score - 10)
        
        current_question = session.current_question.copy()
        session.current_question = None
        
        return {
            "correct": is_correct,
            "correct_answer": correct_answer,
            "feedback": "Correct! 🎵" if is_correct else f"Wrong! The correct answer was '{correct_answer}'",
            "score": session.score,
            "questions_answered": session.questions_answered
        }
    
    def get_session_stats(self, session_id: str) -> Optional[Dict]:
        """Get statistics for a specific session."""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        return {
            "score": session.score,
            "questions_answered": session.questions_answered,
            "accuracy": (session.score / session.questions_answered * 100) if session.questions_answered > 0 else 0
        }
    
    def cleanup_session(self, session_id: str) -> bool:
        """Remove a session from memory."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def get_model_stats(self) -> Dict:
        """Get statistics about the underlying model."""
        return self.ngram_model.get_vocabulary_stats()

    # ---- New helpers for song/part functionality ----
    def _load_raw_lyrics(self) -> List[Dict]:
        """Load raw JSON lyrics for Taylor Swift albums/songs.
        Returns a list of album dicts with nested songs and lyrics.
        """
        try:
            current_file = Path(__file__).resolve()
            backend_dir = current_file.parent.parent
            raw_path = backend_dir / "data" / "raw" / "taylor_swift" / "album-song-lyrics.json"
            if not raw_path.exists():
                return []
            with open(raw_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return []
        except Exception:
            return []

    def _index_songs_by_title(self, albums: List[Dict]) -> Dict[str, Dict]:
        index: Dict[str, Dict] = {}
        for album in albums:
            album_title = album.get("Title", "")
            for song in album.get("Songs", []):
                title = song.get("Title", "").strip()
                if not title:
                    continue
                key = title.lower()
                index[key] = {
                    "title": title,
                    "album": album_title,
                    "lyrics": song.get("Lyrics", [])
                }
        return index

    def _collect_song_parts(self, albums: List[Dict]) -> Dict[str, List[str]]:
        parts_by_title: Dict[str, List[str]] = {}
        for album in albums:
            for song in album.get("Songs", []):
                title = song.get("Title", "").strip()
                if not title:
                    continue
                parts = []
                for line in song.get("Lyrics", []):
                    p = (line.get("SongPart") or "").strip()
                    if p and p not in parts:
                        parts.append(p)
                parts_by_title[title] = parts
        return parts_by_title

    def list_songs(self) -> List[Dict]:
        """Return a list of songs with their album and available parts."""
        songs: List[Dict] = []
        for key, meta in self.songs_index_by_title.items():
            title = meta.get("title", "")
            album = meta.get("album", "")
            parts = self.song_parts_by_title.get(title, [])
            songs.append({
                "title": title,
                "album": album,
                "parts": parts
            })
        # Sort for stable UI
        songs.sort(key=lambda s: (s.get("album", ""), s.get("title", "")))
        return songs

    def _normalize_part(self, part: str) -> Optional[str]:
        if not part:
            return None
        p = part.strip().lower()
        # Map friendly difficulty names to song parts
        if p in ("easy",):
            return "Chorus"
        if p in ("medium",):
            return "Verse"
        if p in ("hard", "difficult", "difficultly", "difficulty", "difficult-level"):
            return "Bridge"
        # Accept direct parts
        mapping = {"chorus": "Chorus", "verse": "Verse", "bridge": "Bridge"}
        return mapping.get(p, part)

    def _generate_ordered_question(self, session: GameSession, song: str, part: str) -> Optional[Dict]:
        title_key = song.strip().lower()
        song_meta = self.songs_index_by_title.get(title_key)
        if not song_meta:
            return None
        normalized_part = self._normalize_part(part)
        if not normalized_part:
            return None
        # Initialize or refresh sequence if song/part changed or empty
        if (
            session.song_title != title_key
            or (session.song_part or "") .lower() != normalized_part.lower()
            or not session.part_lines_ordered
        ):
            # Build ordered lines (by 'Order') with sufficient word count
            lines = [l for l in song_meta.get("lyrics", []) if (l.get("SongPart") or "").strip().lower() == normalized_part.lower()]
            try:
                lines.sort(key=lambda l: int(l.get("Order", 0)))
            except Exception:
                pass
            session.part_lines_ordered = [l for l in lines if isinstance(l.get("Text"), str) and len((l.get("Text") or "").split()) >= 3]
            session.part_index = 0
            session.song_title = title_key
            session.song_part = normalized_part

        if not session.part_lines_ordered:
            return None

        # Select current line and advance index for next call
        line = session.part_lines_ordered[session.part_index % len(session.part_lines_ordered)]
        session.part_index = (session.part_index + 1) % len(session.part_lines_ordered)

        text = (line.get("Text") or "").strip()
        if not text:
            return None
        incomplete_line, correct_word = self._make_incomplete_line(text)
        if not incomplete_line or not correct_word:
            return None
        distractors = self._pick_distractors(correct_word, num=4)
        options = [correct_word] + distractors
        random.shuffle(options)
        return {
            "incomplete_lyric": incomplete_line,
            "correct_answer": correct_word,
            "options": options,
            "question_id": f"q_{random.randint(10000, 99999)}"
        }

    def _make_incomplete_line(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        words = text.split()
        if len(words) < 3:
            return None, None
        # avoid first/last word for better gameplay
        remove_pos = random.randint(1, len(words) - 2)
        correct_word = words[remove_pos]
        words_with_blank = words[:remove_pos] + ["___"] + words[remove_pos+1:]
        return " ".join(words_with_blank), correct_word

    def _pick_distractors(self, correct_word: str, num: int = 4) -> List[str]:
        # Choose distractors from vocabulary different from the correct word
        vocab = list(self.ngram_model.vocabulary)
        # Prefer similar length words
        target_len = len(correct_word)
        candidates = [w for w in vocab if w.lower() != correct_word.lower() and abs(len(w) - target_len) <= 2]
        random.shuffle(candidates)
        distractors: List[str] = []
        for w in candidates:
            if w.lower() != correct_word.lower():
                distractors.append(w)
            if len(distractors) >= num:
                break
        if len(distractors) < num:
            random.shuffle(vocab)
            for w in vocab:
                if w.lower() != correct_word.lower() and w not in distractors:
                    distractors.append(w)
                if len(distractors) >= num:
                    break
        return distractors[:num]

game_manager = GameManager()
