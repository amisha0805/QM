import sqlite3
from fastapi import FastAPI
app = FastAPI()
@app.get("/gcov_data")
def get_gcov_data(comp : str = None,owner : str = None, file : str = None):
    conn = sqlite3.connect("gcov.db",check_same_thread = False)
    cursor = conn.cursor()
    query = "SELECT * FROM gcov_data"
    conditions = []
    params = []
    if comp:
        conditions.append("Component = ?")
        params.append(comp)
    if owner:
        conditions.append("Comp_owner = ?")
        params.append(owner)
    if file:
        conditions.append("Filename = ?")
        params.append(file)
    if conditions:
        query += " WHERE " + " AND " .join(conditions)
    ob = cursor.execute(query,params)
    data = ob.fetchall()
    conn.close()
    return data
