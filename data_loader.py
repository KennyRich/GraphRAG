import requests
import uuid
import hashlib
from config import settings
from typing import Final, Literal
from pydantic import BaseModel
from datetime import datetime
from neo4j import GraphDatabase

PYDATA_BASE_URL: Final[str] = "https://london2024.pydata.org/api/events/cfp"
JINA_READER_BASE_URL: Final[str] = "https://r.jina.ai"


class Speaker(BaseModel):
    name: str
    biography: str
    id: str


class SubmissionInfo(BaseModel):
    id: str
    speaker: Speaker
    title: str
    submission_type: Literal['Talk', 'Tutorial']
    abstract: str
    state: Literal['confirmed']
    description: str
    duration: int
    location: str
    date: str
    start_time: str
    end_time: str


class PyDataSubmissionResult(BaseModel):
    results: list[SubmissionInfo]


class ScrapedWebsite(BaseModel):
    title: str
    url: str
    content: str


def get_pydata_info():
    url = f"{PYDATA_BASE_URL}/submissions?limit=100"
    headers = {
        'Authorization': f'Bearer {settings.PYDATA_API_KEY}'
    }

    response = requests.request("GET", url, headers=headers)

    return response.json()


def extract_date_and_time(date_string: str) -> tuple[str, str]:
    parsed_date = datetime.fromisoformat(date_string)

    date_part = parsed_date.date().isoformat()
    time_part = parsed_date.time().isoformat()

    return date_part, time_part


def parse_data(data: dict) -> PyDataSubmissionResult:
    submissions = data.get("results")
    result: list[SubmissionInfo] = []
    for submission in submissions:
        for speaker in submission.get("speakers"):
            result.append(
                SubmissionInfo(
                    id=str(uuid.uuid4()),
                    speaker=Speaker(
                        id=str(uuid.uuid4()),
                        name=speaker.get("name"),
                        biography=speaker.get("biography") or "Not available",
                    ),
                    title=submission.get("title"),
                    submission_type=submission.get("submission_type").get("en"),
                    abstract=submission.get("abstract"),
                    state=submission.get("state"),
                    description=submission.get("description"),
                    duration=submission.get("duration"),
                    location=submission.get("slot").get("room").get("en"),
                    date=extract_date_and_time(submission.get("slot").get("start"))[0],
                    start_time=extract_date_and_time(submission.get("slot").get("start"))[1],
                    end_time=extract_date_and_time(submission.get("slot").get("end"))[1]
                )
            )

    return PyDataSubmissionResult(results=result)


def scrape_website(url: str) -> ScrapedWebsite:
    url = f"{JINA_READER_BASE_URL}/{url}"
    headers = {
        'Accept': 'application/json',
        'X-No-Cache': 'true'
    }
    response = requests.request("GET", url, headers=headers)
    return ScrapedWebsite(**response.json().get("data"))


def generate_md5_hash(document_text: str) -> str:
    md5_hash = hashlib.md5()
    md5_hash.update(document_text.encode('utf-8'))

    return md5_hash.hexdigest()


def fetch_data() -> PyDataSubmissionResult:
    result = get_pydata_info()
    return parse_data(result)


def load_data_into_database():
    data = fetch_data()
    driver = GraphDatabase.driver(
        uri=settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME,
              settings.NEO4J_PASSWORD)
    )

    def create_nodes_and_relationships(tx, submission: SubmissionInfo):
        tx.run(
            "MERGE (s:Speaker {id: $id, name: $speaker_name, biography: $biography})",
            id=submission.speaker.id,
            speaker_name=submission.speaker.name,
            biography=submission.speaker.biography
        )

        tx.run(
            """
            MERGE (submission:Submission {id:$id, title: $title, submission_type: $submission_type, abstract: $abstract, 
                                          state: $state, description: $description, duration: $duration, 
                                          location: $location, date: $date, start_time: $start_time, 
                                          end_time: $end_time
                                          })
            """,
            id=submission.id,
            title=submission.title,
            submission_type=submission.submission_type,
            abstract=submission.abstract,
            state=submission.state,
            description=submission.description,
            duration=submission.duration,
            location=submission.location,
            date=submission.date,
            start_time=submission.start_time,
            end_time=submission.end_time,
        )

        # Relationship between the Speaker and Submission Node
        tx.run(
            """
            MATCH (s:Speaker {id: $speaker_id}), 
                  (submission:Submission {id: $submission_id})
            MERGE (s)-[:PRESENTED]->(submission)
            """,
            speaker_id=submission.speaker.id,
            submission_id=submission.id
        )

        document_text = f"""
                    This is a submission for a 2024 PyData Conference
                    The title for this submission is: {submission.title} and the abstract is: 
                    {submission.abstract}. And the description is: {submission.description}. The location for the 
                    {submission.submission_type} is at {submission.location} on {submission.date} from 
                    {submission.start_time} to {submission.end_time}.
                    The speaker for the {submission.submission_type} is {submission.speaker.name} and here is their 
                    biography {submission.speaker.biography}
                """

        tx.run(
            """
            MERGE (d:Document {id:$document_id, text: $document_text})
            """,
            document_id=generate_md5_hash(document_text),
            document_text=document_text
        )

        # Relationship between document node and submission node
        tx.run(
            """
            MATCH (d:Document {id: $document_id}), 
                  (submission:Submission {id: $submission_id})
            MERGE (d)-[:MENTIONS]->(submission)
            """,
            document_id=generate_md5_hash(document_text),
            submission_id=submission.id
        )

        # Relationship between the document node and Submission node
        tx.run(
            """
            MATCH (d:Document {id: $document_id}),
                  (speaker:Speaker {id: $submission_id})
            MERGE (d)-[:MENTIONS]->(submission)
            """,
            document_id=generate_md5_hash(document_text),
            submission_id=submission.id
        )

        # Creating relationships between submissions based on type of submission, location and date
        tx.run(
            """
            MATCH (submission1:Submission {id: $submission_id})
            WITH submission1
            MATCH (submission2:Submission)
            WHERE submission1.location = submission2.location AND submission1 <> submission2
            MERGE (submission1)-[:ON_LOCATION]->(submission2)
            """,
            submission_id=submission.id
        )
        tx.run(
            """
            MATCH (submission1:Submission {id: $submission_id})
            WITH submission1
            MATCH (submission2:Submission)
            WHERE submission1.date = submission2.date AND submission1 <> submission2
            MERGE (submission1)-[:ON_DATE]->(submission2)
            """,
            submission_id=submission.id
        )
        tx.run(
            """
            MATCH (submission1:Submission {id: $submission_id})
            WITH submission1
            MATCH (submission2:Submission)
            WHERE submission1.submission_type = submission2.submission_type AND submission1 <> submission2
            MERGE (submission1)-[:ON_TYPE]->(submission2)
            """,
            submission_id=submission.id
        )

    with driver.session() as session:
        for submission in data.results:
            session.write_transaction(create_nodes_and_relationships, submission)

    driver.close()
