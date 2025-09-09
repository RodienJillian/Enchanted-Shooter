import pickle
import random
import re
from collections import defaultdict, Counter
from pathlib import Path
import pandas as pd
import numpy as np
import math

class NGramModel:
    def __init__(self, corpus_path=None):
        """Initialize the N-Gram model with Taylor Swift corpus data."""
        if corpus_path is None:
            current_file = Path(__file__).resolve()
            
            backend_dir = current_file.parent.parent  
            corpus_path = backend_dir / "data" / "processed" / "corpus_json.pkl"
        
        self.corpus_path = corpus_path
        self.corpus_data = None
        self.ngrams = defaultdict(Counter)
        self.vocabulary = set()
        self.load_corpus()
        self.build_ngrams()
    
    def load_corpus(self):
        """Load both corpus data and metadata files for comprehensive lyrics."""
        try:
            base_dir = Path(self.corpus_path).parent
            all_lyrics = []
            
            if self.corpus_path.exists():
                try:
                    with open(self.corpus_path, 'rb') as f:
                        corpus_data = pickle.load(f)
                    
                    # Handle different data types
                    if isinstance(corpus_data, pd.DataFrame):
                        for col in corpus_data.columns:
                            if corpus_data[col].dtype == 'object':
                                sample = str(corpus_data[col].dropna().iloc[0]) if len(corpus_data[col].dropna()) > 0 else ""
                                if len(sample) > 20 and not sample.isdigit() and ' ' in sample:
                                    lyrics_from_corpus = corpus_data[col].dropna().astype(str).tolist()
                                    all_lyrics.extend(lyrics_from_corpus)
                                    break
                    
                    elif isinstance(corpus_data, dict):
                        for key, value in corpus_data.items():
                            if isinstance(value, list):
                                if value and isinstance(value[0], str):
                                    sample = value[0] if len(value) > 0 else ""
                                    if len(sample) > 20 and not sample.isdigit() and ' ' in sample:
                                        all_lyrics.extend(value)
                                        continue
                            
                            elif isinstance(value, str) and len(value) > 20 and ' ' in value:
                                all_lyrics.append(value)
                            
                            elif hasattr(value, '__iter__') and not isinstance(value, str):
                                try:
                                    temp_lyrics = []
                                    for item in value:
                                        if isinstance(item, str) and len(item) > 20 and ' ' in item:
                                            temp_lyrics.append(item)
                                    if temp_lyrics:
                                        all_lyrics.extend(temp_lyrics)
                                except:
                                    continue
                    
                    elif isinstance(corpus_data, list):
                        for item in corpus_data:
                            if isinstance(item, str) and len(item) > 20 and ' ' in item:
                                all_lyrics.append(item)
                    
                    else:
                        try:
                            str_data = str(corpus_data)
                            if len(str_data) > 20 and ' ' in str_data:
                                all_lyrics.append(str_data)
                        except:
                            pass
                    
                except Exception as e:
                    print(f"Warning: Could not load main corpus: {e}")
            else:
                processed_dir = base_dir
                if processed_dir.exists():
                    for pkl_file in processed_dir.glob("*.pkl"):
                        try:
                            with open(pkl_file, 'rb') as f:
                                df = pickle.load(f)
                            if hasattr(df, 'columns'):
                                for col in df.columns:
                                    if df[col].dtype == 'object':
                                        sample = str(df[col].dropna().iloc[0]) if len(df[col].dropna()) > 0 else ""
                                        if len(sample) > 20 and not sample.isdigit() and ' ' in sample:
                                            lyrics_from_file = df[col].dropna().astype(str).tolist()
                                            all_lyrics.extend(lyrics_from_file)
                                            break
                        except Exception as e:
                            continue
            
            metadata_dir = base_dir / "metadata"
            if metadata_dir.exists():
                lyrics_file = metadata_dir / "cots-lyric-details.tsv"
                if lyrics_file.exists():
                    try:
                        for encoding in ['latin-1', 'cp1252', 'iso-8859-1', 'utf-8']:
                            try:
                                metadata_df = pd.read_csv(lyrics_file, sep='\t', encoding=encoding)
                                
                                lyrics_column = None
                                for col in metadata_df.columns:
                                    if 'lyric' in col.lower() or 'text' in col.lower() or 'word' in col.lower():
                                        sample = str(metadata_df[col].dropna().iloc[0]) if len(metadata_df[col].dropna()) > 0 else ""
                                        if len(sample) > 10 and not sample.isdigit():
                                            lyrics_column = col
                                            break
                                
                                if not lyrics_column:
                                    for col in metadata_df.columns:
                                        if metadata_df[col].dtype == 'object':
                                            sample = str(metadata_df[col].dropna().iloc[0]) if len(metadata_df[col].dropna()) > 0 else ""
                                            if len(sample) > 20 and not sample.isdigit() and ' ' in sample:
                                                lyrics_column = col
                                                break
                                
                                if lyrics_column:
                                    metadata_lyrics = metadata_df[lyrics_column].dropna().astype(str).tolist()
                                    all_lyrics.extend(metadata_lyrics)
                                
                                break
                                
                            except UnicodeDecodeError:
                                continue
                            except Exception as e:
                                continue
                    
                    except Exception as e:
                        pass
                
                for metadata_file in metadata_dir.glob("*.tsv"):
                    if metadata_file.name != "cots-lyric-details.tsv":
                        try:
                            for encoding in ['latin-1', 'cp1252']:
                                try:
                                    df = pd.read_csv(metadata_file, sep='\t', encoding=encoding)
                                    for col in df.columns:
                                        if df[col].dtype == 'object':
                                            sample = str(df[col].dropna().iloc[0]) if len(df[col].dropna()) > 0 else ""
                                            if len(sample) > 30 and not sample.isdigit() and ' ' in sample:
                                                additional_lyrics = df[col].dropna().astype(str).tolist()
                                                all_lyrics.extend(additional_lyrics)
                                                break
                                    break
                                except:
                                    continue
                        except Exception as e:
                            continue
            
            if all_lyrics:
                unique_lyrics = list(set(all_lyrics))
                
                self.corpus_data = pd.DataFrame({'lyrics': unique_lyrics})
                print(f"✅ Loaded corpus with {len(unique_lyrics)} unique lyrics")
                
            else:
                print("❌ No lyrics data found from any source!")
                self.corpus_data = pd.DataFrame()
                
        except Exception as e:
            print(f"Error loading combined corpus: {e}")
            self.corpus_data = pd.DataFrame()
    
    def build_ngrams(self, n=3):
        """Build n-gram model from the combined lyrics data."""
        if self.corpus_data.empty:
            return
        
        if 'lyrics' in self.corpus_data.columns:
            lyrics_data = self.corpus_data['lyrics'].dropna().tolist()
        else:
            print("❌ Expected 'lyrics' column not found in combined data!")
            return
        
        valid_lyrics_count = 0
        skipped_count = 0
        
        for lyrics in lyrics_data:
            if pd.isna(lyrics) or lyrics == 'nan' or lyrics == 'None':
                continue
            
            words = re.findall(r'\b[a-zA-Z]+\b', lyrics.lower())
            
            if len(words) < n:
                skipped_count += 1
                continue
            
            if len(words) > 500:
                skipped_count += 1
                continue
            
            if any(word.isdigit() for word in words):
                skipped_count += 1
                continue
                
            self.vocabulary.update(words)
            
            for i in range(len(words) - n + 1):
                ngram = tuple(words[i:i+n])
                if len(ngram) == n:
                    self.ngrams[ngram[:-1]][ngram[-1]] += 1
            
            valid_lyrics_count += 1
        
        print(f"✅ Built model: {len(self.vocabulary)} words, {len(self.ngrams)} n-grams")
        
        if valid_lyrics_count == 0:
            print("❌ Warning: No valid lyrics processed!")
    
    def get_next_word_probabilities(self, context):
        """Get probability distribution for next word given context."""
        if context not in self.ngrams:
            return {}
        
        total = sum(self.ngrams[context].values())
        if total == 0:
            return {}
        
        return {word: count/total for word, count in self.ngrams[context].items()}
    
    def generate_incomplete_lyric(self, min_length=5, max_length=10):
        """Generate an incomplete lyric line with a missing word."""
        if not self.ngrams:
            return None, None, []
        
        available_contexts = list(self.ngrams.keys())
        if not available_contexts:
            return None, None, []
        
        context = random.choice(available_contexts)
        words = list(context)
        
        line_length = random.randint(min_length, max_length)
        
        for _ in range(line_length - len(context)):
            if context in self.ngrams and self.ngrams[context]:
                probs = self.get_next_word_probabilities(context)
                if probs:
                    next_word = random.choices(list(probs.keys()), weights=list(probs.values()))[0]
                    words.append(next_word)
                    context = context[1:] + (next_word,)
                else:
                    break
            else:
                break
        
        if len(words) < 3:
            return None, None, []
        
        remove_pos = random.randint(1, len(words) - 2)
        correct_word = words[remove_pos]
        
        incomplete_words = words[:remove_pos] + ['___'] + words[remove_pos + 1:]
        incomplete_line = ' '.join(incomplete_words)
        
        distractors = self.generate_distractors(correct_word, words)
        
        return incomplete_line, correct_word, distractors
    
    def generate_distractors(self, correct_word, context_words, num_distractors=4):
        """Generate plausible but incorrect word options."""
        distractors = []
        
        similar_words = set()
        for context in self.ngrams:
            if any(word in context for word in context_words):
                similar_words.update(self.ngrams[context].keys())
        
        similar_words.discard(correct_word)
        
        random_words = list(self.vocabulary - {correct_word})
        random.shuffle(random_words)
        
        candidate_words = list(similar_words) + random_words[:100]
        random.shuffle(candidate_words)
        
        for word in candidate_words:
            if word != correct_word and word not in distractors:
                distractors.append(word)
                if len(distractors) >= num_distractors:
                    break
        
        while len(distractors) < num_distractors and len(random_words) > 0:
            word = random_words.pop()
            if word != correct_word and word not in distractors:
                distractors.append(word)
        
        return distractors[:num_distractors]
    
    def get_vocabulary_stats(self):
        """Get statistics about the vocabulary and n-grams."""
        return {
            'vocabulary_size': len(self.vocabulary),
            'ngram_count': len(self.ngrams),
            'total_ngrams': sum(sum(counter.values()) for counter in self.ngrams.values())
        }
    
    def interpolated_prob(self, context, word, lambdas=(0.1, 0.3, 0.6)):
        unigram_prob = self.get_ngram_prob((), word, n=1)
        bigram_prob = self.get_ngram_prob((context[-1],), word, n=2) if len(context) >= 1 else 0
        trigram_prob = self.get_ngram_prob(context[-2:], word, n=3) if len(context) >= 2 else 0

        return lambdas[0]*unigram_prob + lambdas[1]*bigram_prob + lambdas[2]*trigram_prob
    
    def get_ngram_prob(self, context, word, n=2, smoothing=True):

        counts = self.ngram_counts[n]
        vocab_size = len(self.vocab)

        context_tuple = tuple(context[-(n-1):]) if n > 1 else ()
        numerator = counts[context_tuple].get(word, 0)

        if smoothing:
            numerator += 1
            denominator = sum(counts[context_tuple].values()) + vocab_size
        else:
            denominator = sum(counts[context_tuple].values())

        return numerator / denominator if denominator > 0 else 0
    
    import math

    def perplexity(self, test_sequence, n=3):
        N = len(test_sequence)
        log_prob_sum = 0

        for i in range(n-1, N):
            context = tuple(test_sequence[i-n+1:i])
            word = test_sequence[i]
            prob = self.get_ngram_prob(context, word, n=n, smoothing=True)
            if prob > 0:
                log_prob_sum += math.log(prob)
            else:
                log_prob_sum += float('-inf')

        return math.exp(-log_prob_sum / N)