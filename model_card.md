# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Give your model a short, descriptive name.  
Stracker  

---

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 

Prompts:  

- What kind of recommendations does it generate  
- What assumptions does it make about the user  
- Is this for real users or classroom exploration  

The model recommends the top songs from data.csv that a specific user profile might want to listen to. 

It assumes the user can be reduced to a simple taste profile, a list of preferences that the recommender can use to score songs. 

This recommender is purely for classroom exploration, a real algorithm would need to be able to learn from data and work with a bigger dataset. 

---

## 3. How the Model Works  

Explain your scoring approach in simple language.  

Prompts:  

- What features of each song are used (genre, energy, mood, etc.)  
- What user preferences are considered  
- How does the model turn those into a score  
- What changes did you make from the starter logic  

Avoid code here. Pretend you are explaining the idea to a friend who does not program.

The model works by comparing songs in the dataset to user preferences given in a user taste profile. It looks at features of the song like genre, mood, energy, and acousticness. Songs are scored higher when they have matching features or the numeric features are close in value to the user's preference. Different features have different weights, so features like genre matter more than energy or tempo. Once each song has a score, the system ranks them and recommends the top songs to the user. 

---

## 4. Data  

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  
- What genres or moods are represented  
- Did you add or remove data  
- Are there parts of musical taste missing in the dataset  

---

There are 18 songs in the catalog. It originally begain with 10, but I added 8 songs to introduce variety in genre and mood. Each song has categorical features like genre and mood plus numeric features like energy, tempo, and duration. The dataset has styles like pop, lofi, rock, jazz, classical, house, metal, and blues. Of course there are parts of musical taste missing in the dataset, I can't possibly represent all different musical tastes with a csv file, much less a csv file with 18 entries. 

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  

The system works pretty well with the user profiles that I initially came up with that have well defined, consistent characteristics. The high energy pop and chill lofi profiles for example got served exactly the songs you would expect them to. When the data is nice and user listening isn't extraordinarily complex and multi faceted, the model works as intended. 

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider  
- Genres or moods that are underrepresented  
- Cases where the system overfits to one preference  
- Ways the scoring might unintentionally favor some users  

The model is pretty severely limited. It only works with this tiny little csv dataset, so the recommendations are biased towards whatever is included. It focuses on reasonably measurable features, whether categorical or numerical, but steers clear of more complex features like lyrics, song structure, or musical choices made. It also struggles with contradictory profiles since the scoring system only adds points and never removes points, there's no sense of cancelling out contradictions. The scoring may unintentionally favor users with similar taste to the music in the dataset, since unfortunately users that don't like any of the music in the dataset are kind of cooked. 

---

## 7. Evaluation  

- Which user profiles you tested  
- What you looked for in the recommendations  
- What surprised you  
- Any simple tests or comparisons you ran  

I tested six profiles in `src/main.py`: High-Energy Pop, Chill Lofi, Deep Intense Rock, Conflicting Preferences, Unsupported Mood Edge Case, and Impossible Hybrid. I looked at the top songs, their scores, and the explanation reasons.

The clearest results came from the realistic profiles. High-Energy Pop returned songs like `Sunrise City` and `Gym Hero`. Chill Lofi returned `Midnight Coding`, `Library Rain`, and `Focus Flow`. Deep Intense Rock returned `Storm Runner` first. That made sense because those songs matched the profile on genre, mood, and the main numeric features.

What surprised me most was how often `Gym Hero` showed up. It appeared even when the profile was not really asking for a workout song. This happened because the model adds points for partial matches. `Gym Hero` is very high-energy and close on tempo and popularity, so it keeps earning points.

The edge cases showed the limits of the system. Conflicting Preferences still returned mostly lofi songs because genre stayed strong even when the other features pulled in another direction. Unsupported Mood Edge Case showed that if no song matches the mood, the system falls back to genre and numeric similarity. Impossible Hybrid returned a mixed set of songs because no single song matched the whole profile.

I also compared profile pairs to see what changed. High-Energy Pop and Chill Lofi gave very different outputs because one profile wanted bright, fast songs and the other wanted slower, softer songs. High-Energy Pop and Deep Intense Rock overlapped more because both wanted high energy, which helps explain why `Gym Hero` kept showing up. Chill Lofi and Conflicting Preferences were useful too, because both leaned toward lofi, but the conflicting profile looked less clean since its preferences did not fit together well.

---

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
- Better ways to explain recommendations  
- Improving diversity among the top results  
- Handling more complex user tastes  

I'd add an actual learning model aka machine learning. I'd also want to wire it up to an API or some other data source instead of a csv so the recommender has real variety to choose from. To increase diversity, it might make sense to choose a random subset of the dataset to run the model on, that way recommendations will change from run to run. I think pivoting to a machine learning model would also allow the system to handle more complex user tastes. As long as we can embed features, we can throw complex song data at the model and have it spit out recommendations.

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  

I learned a lot about real world recommender systems and all their different phases. It was interesting translating that into a simpler system to actually implement. I didn't realize how much actually went into the recommendation system and that they even use other people's profiles and data to recommend things to you. This made me excited about music recommendation, I'm looking forward to exploring this project and seeing what I can do to elevate the project to a real recommendation algorithm.

My biggest learning moment during this project was learning about the infrastructure and resources necessary to actually launch a successful recommender system. It all starts with a real, substantial dataset rather than a play csv. Using AI tools during this project was exceptionally productive, though there were some cases when AI would leave behind legacy code and rack up technical debt since it was so focuesed on moving forward and iterating. I was surprised with how effective this simple algorithm was though, with the right features and the right preferences, distinct users can get strong, personalized recommendations simply by matching and comparing values.