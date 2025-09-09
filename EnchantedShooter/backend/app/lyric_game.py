import random
from typing import List, Tuple, Optional
from ngram_model import NGramModel

class LyricGuesserGame:
    def __init__(self, corpus_path=None):
        """Initialize the Lyric Guesser game."""
        self.ngram_model = NGramModel(corpus_path)
        self.score = 0
        self.total_questions = 0
        self.current_question = None
        self.game_history = []
        
    def start_new_game(self):
        """Start a new game session."""
        self.score = 0
        self.total_questions = 0
        self.game_history = []
        print("🎵 Welcome to Taylor Swift Lyric Guesser! 🎵")
        print("Fill in the missing word in each lyric line.")
        print("You'll get 5 options - only one is correct!")
        print("-" * 50)
    
    def generate_question(self) -> Optional[Tuple[str, str, List[str]]]:
        """Generate a new question with incomplete lyrics and options."""
        try:
            incomplete_line, correct_word, distractors = self.ngram_model.generate_incomplete_lyric()
            
            if not incomplete_line or not correct_word or len(distractors) < 4:
                return None
            
            # Create multiple choice options
            options = [correct_word] + distractors[:4]
            random.shuffle(options)
            
            # Store current question
            self.current_question = {
                'incomplete_line': incomplete_line,
                'correct_word': correct_word,
                'options': options,
                'correct_index': options.index(correct_word)
            }
            
            return incomplete_line, correct_word, options
            
        except Exception as e:
            print(f"Error generating question: {e}")
            return None
    
    def display_question(self):
        """Display the current question to the user."""
        if not self.current_question:
            return False
        
        print(f"\nQuestion {self.total_questions + 1}")
        print("-" * 30)
        print(f"Complete this lyric:")
        print(f"'{self.current_question['incomplete_line']}'")
        print("\nOptions:")
        
        for i, option in enumerate(self.current_question['options'], 1):
            print(f"{i}. {option}")
        
        return True
    
    def check_answer(self, user_choice: int) -> Tuple[bool, str]:
        """Check if the user's answer is correct."""
        if not self.current_question:
            return False, "No active question"
        
        if user_choice < 1 or user_choice > 5:
            return False, "Invalid choice. Please select 1-5."
        
        user_answer = self.current_question['options'][user_choice - 1]
        correct_answer = self.current_question['correct_word']
        is_correct = user_answer == correct_answer
        
        # Update score
        if is_correct:
            self.score += 1
            feedback = f"🎉 Correct! '{correct_answer}' is the right word!"
        else:
            feedback = f"❌ Wrong! The correct answer was '{correct_answer}'"
        
        # Update game state
        self.total_questions += 1
        self.game_history.append({
            'question': self.current_question['incomplete_line'],
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct
        })
        
        # Clear current question
        self.current_question = None
        
        return is_correct, feedback
    
    def get_score(self) -> Tuple[int, int, float]:
        """Get current score statistics."""
        percentage = (self.score / self.total_questions * 100) if self.total_questions > 0 else 0
        return self.score, self.total_questions, percentage
    
    def display_score(self):
        """Display current score."""
        score, total, percentage = self.get_score()
        print(f"\n📊 Score: {score}/{total} ({percentage:.1f}%)")
    
    def display_final_results(self):
        """Display final game results."""
        print("\n" + "=" * 50)
        print("🎵 GAME OVER! 🎵")
        print("=" * 50)
        
        score, total, percentage = self.get_score()
        print(f"Final Score: {score}/{total} ({percentage:.1f}%)")
        
        if percentage >= 90:
            print("🏆 Outstanding! You're a Taylor Swift expert!")
        elif percentage >= 75:
            print("🥇 Great job! You know your Taylor Swift lyrics!")
        elif percentage >= 60:
            print("🥈 Good effort! Keep listening to Taylor Swift!")
        elif percentage >= 40:
            print("🥉 Not bad! More Taylor Swift listening needed!")
        else:
            print("💪 Keep practicing! Taylor Swift has so many great songs!")
        
        print("\nQuestion History:")
        for i, q in enumerate(self.game_history, 1):
            status = "✅" if q['is_correct'] else "❌"
            print(f"{i}. {status} {q['question']}")
            if not q['is_correct']:
                print(f"   Your answer: '{q['user_answer']}' | Correct: '{q['correct_answer']}'")
    
    def get_game_stats(self) -> dict:
        """Get comprehensive game statistics."""
        return {
            'score': self.score,
            'total_questions': self.total_questions,
            'percentage': self.get_score()[2],
            'vocabulary_stats': self.ngram_model.get_vocabulary_stats(),
            'game_history': self.game_history
        }

class LyricGame:
    def __init__(self, ngram_model, difficulty="medium"):
        self.ngram_model = ngram_model
        self.difficulty = difficulty.lower()
        self.n_value = self._get_n_value()

    def _get_n_value(self):
        if self.difficulty == "easy":
            return 1  # Unigram
        elif self.difficulty == "medium":
            return 2  # Bigram
        elif self.difficulty == "hard":
            return 3  # Trigram (or higher)
        return 2  # Default to bigram

    def get_question(self):
        return self.ngram_model.generate_question(n=self.n_value)
