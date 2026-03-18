from interview_engine.question_generator import generate_question
from database import session_crud
from database.db import init_db


def test_adaptive_session_flow(tmp_path):
    # initialize DB tables (safe to call repeatedly)
    init_db()

    sid = "test-adaptive-001"
    # create session with role
    session_crud.create_session(sid, role="ml")

    # first question
    qtext = generate_question("ml", [])
    q = session_crud.create_question(sid, 1, qtext)

    # simulate an answer that contains ML keywords
    answer_text = "I used convolutional layers, backprop and regularization to prevent overfitting"
    session_crud.save_answer(sid, q.id, 0.85, 0.8, 0.7, 0.9, answer_text=answer_text, keywords=["convolution","backprop"])

    # request next question (generator will look at last answer via session_crud)
    qs = session_crud.get_questions(sid)
    history = [q["question_text"] for q in qs]
    # call generator with last answer directly as a unit test
    next_q = generate_question("ml", history, last_answer=answer_text)
    assert isinstance(next_q, str) and len(next_q) > 10
