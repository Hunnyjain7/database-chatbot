import mysql.connector
import logging
import os

from dotenv import load_dotenv
from mysql.connector import errorcode
from openai import OpenAI

load_dotenv()


# Replace 'your-openai-api-key' with your actual OpenAI API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Ensure the API key is available
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key is missing from environment variables")


client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(level=logging.INFO)

 
def connect_to_database(user, password, host, database):
    try:
        connection = mysql.connector.connect(
            user=user,
            password=password,
            host=host,
            database=database
        )
        return connection
    except mysql.connector.Error as err:
        logging.error(f"Database connection error: {err}")
        return None

def get_schema(cursor):
    try:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        schema = {}
        for (table_name,) in tables:
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            schema[table_name] = {column[0]: column[1] for column in columns}
        return schema
    except mysql.connector.Error as err:
        logging.error(f"Error fetching schema: {err}")
        return {}

def summarize_schema(schema):
    summary = []
    for table_name, columns in schema.items():
        column_summary = [f"{column_name} ({column_type})" for column_name, column_type in columns.items()]
        summary.append(f"Table {table_name}: " + ", ".join(column_summary))
    return "\n".join(summary)

def generate_sql_query(question, schema_summary):
    prompt = (
        f"Schema Summary: {schema_summary}\n"
        f"Question: {question}\n"
        "\n"
        "Note: Ensure to handle date inputs correctly, whether only date or datetime is provided. Use SQL functions such as DATE() or STR_TO_DATE() as required, and always alias columns with 'AS' for clarity."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates SQL queries based on the database schema and user questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        query = response.choices[0].message.content.strip()
        if "```" in query:
            query = query.split("```")[1].strip()
            if query.lower().startswith("sql"):
                query = query[3:].strip()
                logging.info(f"Query: {query}")
                print("SQL Query:", query)
        return query
    except Exception as e:
        logging.error(f"Error generating SQL query: {e}")
        return None

def fetch_data(cursor, query):
    try:
        results = []
        for result in cursor.execute(query, multi=True):
            if result.with_rows:
                columns = [desc[0] for desc in result.description]
                rows = result.fetchall()
                results.append((columns, rows))
        return results
    except mysql.connector.Error as err:
        logging.error(f"Error fetching data: {err}")
        return []

def generate_html_response(query, result_sets):
    html_parts = []

    for columns, results in result_sets:
        table_html = "<table border='1'><tr>"
        for col in columns:
            table_html += f"<th>{human_readable_header(col)}</th>"
        table_html += "</tr>"
        for row in results:
            table_html += "<tr>"
            for cell in row:
                table_html += f"<td>{cell}</td>"
            table_html += "</tr>"
        table_html += "</table>"
        html_parts.append(table_html)

    html = "<html><body>" + "".join(html_parts) + "</body></html>"
    return html

def human_readable_header(header):
    return header.replace('_', ' ').title()

def handle_question(query, user, password, host, database):
    connection = connect_to_database(user, password, host, database)
    if not connection:
        return {"status": 0, "data": None, "message": "Database connection failure."}

    cursor = connection.cursor()
    schema = get_schema(cursor)
    if not schema:
        cursor.close()
        return {"status": 0, "data": None, "message": "Failed to fetch database schema."}

    schema_summary = summarize_schema(schema)
    logging.info(f"Schema Summary: {schema_summary}")  # Log the schema summary for comparison
    sql_query = generate_sql_query(query, schema_summary)
    if not sql_query:
        cursor.close()
        return {"status": 0, "data": None, "message": "Failed to generate SQL query."}

    result_sets = fetch_data(cursor, sql_query)
    if not result_sets:
        cursor.close()
        return {"status": 0, "data": None, "message": "I'm having trouble understanding your message. Can you please clarify?"}

    if not result_sets[0][1]:
        cursor.close()
        return {"status": 0, "data": None, "message": "No data found"}

    html_response = generate_html_response(query, result_sets)
    cursor.close()
    return {"status": 1, "data": html_response, "message": "Data retrieved successfully"}
