from fastapi import FastAPI
from lyric_game import LyricGuesserGame
import sys

def main():
    print("🎵 Loading Taylor Swift Lyric Guesser... 🎵")
    
    try:
        game = LyricGuesserGame()
        
        stats = game.ngram_model.get_vocabulary_stats()
        if stats['vocabulary_size'] == 0:
            print("❌ Error: Could not load corpus data. Please check the data files.")
            return
        
        print(f"✅ Corpus loaded successfully!")
        print(f"📚 Vocabulary size: {stats['vocabulary_size']} words")
        print(f"🔗 N-grams: {stats['ngram_count']}")
        
        game.start_new_game()
        
        while True:
            question_data = game.generate_question()
            if not question_data:
                print("❌ Could not generate a question. Please try again.")
                break
            
            if not game.display_question():
                break
            
            while True:
                try:
                    user_input = input("\nEnter your choice (1-5) or 'q' to quit: ").strip().lower()
                    
                    if user_input == 'q':
                        print("\n👋 Thanks for playing! Goodbye!")
                        game.display_final_results()
                        return
                    
                    user_choice = int(user_input)
                    if 1 <= user_choice <= 5:
                        break
                    else:
                        print("❌ Please enter a number between 1 and 5.")
                except ValueError:
                    print("❌ Please enter a valid number (1-5) or 'q' to quit.")
            
            is_correct, feedback = game.check_answer(user_choice)
            print(f"\n{feedback}")
            
            game.display_score()
            
            while True:
                continue_game = input("\nContinue to next question? (y/n): ").strip().lower()
                if continue_game in ['y', 'yes']:
                    break
                elif continue_game in ['n', 'no']:
                    print("\n👋 Thanks for playing!")
                    game.display_final_results()
                    return
                else:
                    print("Please enter 'y' or 'n'.")
     
    except KeyboardInterrupt:
        print("\n\n👋 Game interrupted. Thanks for playing!")
        game = LyricGuesserGame()  # Ensure game is initialized for final results
        if 'game' in locals() and game:
            game.display_final_results()
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please check your data files and try again.")

if __name__ == '__main__':
    main()
