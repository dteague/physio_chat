# TODO
Immediate todos for project:

- [ ] Add tests with CI for the github area
- [ ] Optimize AI responses by fixing system messages and input options
- [ ] Add cycle to patient responses to make responses sound more natural (avoiding technical language inherited from RAG facts)
- [ ] Refine HyDE to improve embedding retrieval
- [ ] Split message types into patient responses and role-play response (results of test or exercise or evaluation) both visually in chat message and in database
- [ ] Setup docker for wrapping app
- [ ] Add tests for web interface (namely check automatic updating). May be unnecessary when move to modern web frontend

## Longer term goals

- [ ] Test basic logic with physical therapist to gauge treatment evaluation and patient realism
- [ ] Connect larger model to app for better performance/speed
- [ ] Migrate SQL more robust database (eg Postgres with pgvector for ANN/embedding retrieval)
- [ ] Migrate web interface to separate server and implement webpage with more modern setup (React or VueJS for instance)
- [ ] Implement student mode (only view chats for their login) and teacher mode (can review all chats, possibly with some summary for each student's chat)
- [ ] Add more disorders/articles for more variety
