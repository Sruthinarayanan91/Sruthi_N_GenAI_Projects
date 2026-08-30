from pathlib import Path
import sqlite3
import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS suppliers (
 supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
 supplier_name TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS criteria (
 criterion_id INTEGER PRIMARY KEY,
 name TEXT NOT NULL,
 weight REAL NOT NULL,
 max_score REAL NOT NULL,
 active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS criterion_evaluations (
 evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
 supplier_id INTEGER NOT NULL,
 criterion_id INTEGER NOT NULL,
 score REAL NOT NULL,
 justification TEXT,
 evidence TEXT,
 FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
 FOREIGN KEY (criterion_id) REFERENCES criteria(criterion_id)
);
CREATE TABLE IF NOT EXISTS supplier_results (
 result_id INTEGER PRIMARY KEY AUTOINCREMENT,
 supplier_id INTEGER NOT NULL,
 weighted_score REAL NOT NULL,
 percentage_score REAL NOT NULL,
 ppi REAL NOT NULL,
 rank INTEGER NOT NULL,
 overall_summary TEXT,
 FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);
CREATE TABLE IF NOT EXISTS supplier_risks (
 supplier_id INTEGER PRIMARY KEY,
 risks_json TEXT NOT NULL,
 FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);
"""

def get_connection(db_path):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(db_path, check_same_thread=False)
    c.execute("PRAGMA foreign_keys=ON")
    return c

def initialize_database(conn):
    conn.executescript(SCHEMA); conn.commit()

def seed_default_criteria(conn):
    rows = [
        (1,"Technical Capability",30,10),
        (2,"Implementation Plan",20,10),
        (3,"Commercial Value",20,10),
        (4,"Security & Compliance",20,10),
        (5,"Support & Experience",10,10),
    ]
    conn.executemany("INSERT OR REPLACE INTO criteria VALUES (?,?,?,?,1)", rows)
    conn.commit()

def get_active_criteria(conn):
    return pd.read_sql_query(
        "SELECT criterion_id,name,weight,max_score FROM criteria WHERE active=1 ORDER BY criterion_id", conn)

def criteria_to_text(df):
    return "\n".join(
        f"{int(r.criterion_id)}. {r.name} (weight={r.weight}%, max_score={r.max_score})"
        for r in df.itertuples()
    )

def save_evaluation(conn, evaluation, scorecard, ppi, rank):
    conn.execute("INSERT OR IGNORE INTO suppliers(supplier_name) VALUES(?)",(evaluation.supplier_name,))
    sid = conn.execute("SELECT supplier_id FROM suppliers WHERE supplier_name=?",(evaluation.supplier_name,)).fetchone()[0]
    conn.execute("DELETE FROM criterion_evaluations WHERE supplier_id=?",(sid,))
    conn.execute("DELETE FROM supplier_results WHERE supplier_id=?",(sid,))
    for item in scorecard["criteria"]:
        conn.execute("""INSERT INTO criterion_evaluations
        (supplier_id,criterion_id,score,justification,evidence) VALUES(?,?,?,?,?)""",
        (sid,item["criterion_id"],item["score"],item["justification"],item["evidence"]))
    conn.execute("""INSERT INTO supplier_results
    (supplier_id,weighted_score,percentage_score,ppi,rank,overall_summary)
    VALUES(?,?,?,?,?,?)""",
    (sid,scorecard["total_score"],scorecard["percentage_score"],ppi,rank,evaluation.overall_summary))
    import json
    conn.execute("INSERT OR REPLACE INTO supplier_risks(supplier_id,risks_json) VALUES(?,?)",
                 (sid,json.dumps(evaluation.risks)))
    conn.commit()

def get_ranking(conn):
    return pd.read_sql_query("""
    SELECT s.supplier_name,r.weighted_score,r.percentage_score,r.ppi,r.rank
    FROM supplier_results r JOIN suppliers s ON r.supplier_id=s.supplier_id
    ORDER BY r.rank""", conn)

def get_supplier_detail(conn, name):
    result = pd.read_sql_query("""
    SELECT s.supplier_name,r.weighted_score,r.percentage_score,r.ppi,r.rank,r.overall_summary
    FROM supplier_results r JOIN suppliers s ON r.supplier_id=s.supplier_id
    WHERE s.supplier_name=?""", conn, params=(name,))
    criteria = pd.read_sql_query("""
    SELECT c.name,c.weight,c.max_score,e.score,e.justification,e.evidence
    FROM criterion_evaluations e
    JOIN suppliers s ON e.supplier_id=s.supplier_id
    JOIN criteria c ON e.criterion_id=c.criterion_id
    WHERE s.supplier_name=? ORDER BY c.criterion_id""", conn, params=(name,))
    risks_df = pd.read_sql_query("""
    SELECT sr.risks_json FROM supplier_risks sr
    JOIN suppliers s ON sr.supplier_id=s.supplier_id
    WHERE s.supplier_name=?""", conn, params=(name,))
    return result, criteria, risks_df
