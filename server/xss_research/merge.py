from models import Finding, TriageStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def increment_keys():
    engine = create_engine('sqlite:///../xss_research2.db')
    Session = sessionmaker(bind = engine)
    session = Session()
    for i in range(1,87):
        session.query(Finding.id).\
            filter(Finding.id == i).\
            update({"id": (Finding.id + 603)})
        session.commit()


if __name__ == "__main__":
    increment_keys()