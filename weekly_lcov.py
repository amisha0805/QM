import subprocess
import sys
import shutil
import os
import glob
import argparse
import sqlite3
conn = sqlite3.connect("/home/amisha/GCOV/LCOV_automation/gcov.db",check_same_thread = False)
cursor = conn.cursor()
def get_source_code(source,dest):
    try:
        shutil.copytree(source,dest,dirs_exist_ok=True)
    except Exception as e:
        print(f"Copy Failed :( {e}")
    return

def check(res,success,fail):
    if res.returncode == 0:
        print(success)
    else:
        print(fail)
        sys.exit(1)

def build(dest):
    os.chdir(dest)
    c_files = glob.glob("*.c")
    for file in c_files:
        binary_name = f"./temp_{os.path.splitext(file)[0]}"
        res = subprocess.run(f"gcc -fprofile-arcs -ftest-coverage {file} -o {binary_name}",shell = True, capture_output=True, text=True)
        check(res,"Build successful :)","Build Failure :(")
        if res.returncode == 0:
            run_res = subprocess.run(binary_name, shell=True,capture_output=True,text=True)
            check(run_res,"GCDA generated :)","Failed to generate GCDA :(")

def capture_lcov_data(dest):
    os.chdir(dest)
    bash_path = shutil.which('bash')
    lcov_cmnd = 'lcov --capture --directory . --output-file coverage.info'
    res = subprocess.run(lcov_cmnd, capture_output=True, text=True, shell=True)
    check(res, "LCOV Data Captured ;)", "Failed to capture LCOV Data:(")
    if res.returncode == 0:
        with open("coverage.info", "r") as file:
            coverage_data = {}
            raw_lines = {}
            filename = "Unknown"

            for line in file:
                if line.startswith("SF:"):
                    filename = line.split(":", 1)[1].strip()
                    coverage_data[filename] = []
                    raw_lines[filename] = []
                elif line.startswith("DA:"):
                    if filename != "Unknown":
                        l = line.split(":", 1)[1].strip()
                        parts = l.split(",")
                        if int(parts[1]) > 0:
                            raw_lines[filename].append(int(parts[0]))
                elif line.startswith("LF:"):
                    lf_total = int(line.split(":", 1)[1].strip())
                elif line.startswith("LH:"):
                    lh_hit = int(line.split(":", 1)[1].strip())
                elif line.strip() == "end_of_record":
                    if filename != "Unknown":
                        raw_lines[filename].sort()
                        lines_str = ",".join(str(num) for num in raw_lines[filename])
                        percentage = round((lh_hit / lf_total) * 100, 2) if lf_total > 0 else 0.0
                        coverage_data[filename] = (lines_str, percentage)

        with open(f"{dest}/coverage_lines", "w") as new_file:
            for file_key, data in coverage_data.items():
                lines = data[0]
                new_file.write(f"{file_key}:{lines}\n")
        print("Coverage lines generated")
        print(coverage_data)
        return coverage_data


def insert_into_db(coverage_data):
    for file,data in coverage_data.items():
        filename = file
        line_numbers = data[0]
        lcov_percentage = data[1]
        with open("/home/amisha/GCOV/LCOV_automation/comp2file.txt","r") as comp_file:
            for li in comp_file:
                li = li.strip()
                parts = li.split(";:;")
                print(f"DEBUG - Filename from LCOV: '{filename}'")
                print(f"DEBUG - Content of parts[2]: '{parts[2]}' if len is {len(parts)}")
                print("DEBUG: Checking file -> LCOV: '{filename}' vs CompMap: '{parts[2]}'")
                if len(parts) == 4 and filename == parts[2]:
                    comp =  parts[0]
                    comp_owner = parts[1]
                    shipped = parts[3]
                    cursor.execute("SELECT Line_numbers from gcov_data where Filename = ?",(filename,))
                    row = cursor.fetchone()
                    if row:
                        existing_lines = row[0]
                        if existing_lines != line_numbers:
                            cursor.execute("UPDATE gcov_data set Line_numbers = ?,LCOV = ? WHERE Filename = ?",(line_numbers,lcov_percentage,filename))
                    else:
                        cursor.execute("""INSERT INTO gcov_data (Component,Filename,LCOV,Line_numbers,Comp_owner,Shipped) VALUES (?,?,?,?,?,?)""",(comp,filename,lcov_percentage,line_numbers,comp_owner,shipped))
    conn.commit()
    conn.close()
    print("File inserted")

def gen_html(dest):
    os.chdir(dest)
    bash_path = shutil.which('bash')
    cmnd = 'genhtml coverage.info --output-directory html_dir'
    res = subprocess.run(cmnd,capture_output=True, text=True,shell=True)
    check(res,"HTML Report Generated :)", "Failed to generate HTML Report :(")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=str, required=True, help="Path to the source directory")
    parser.add_argument("--dest", type=str, required=True, help="Path to destination directory")
    args=parser.parse_args()
    abs_source = os.path.abspath(args.source)
    abs_dest = os.path.abspath(args.dest)
    get_source_code(abs_source,abs_dest)
    build(abs_dest)
    coverage_data = capture_lcov_data(abs_dest)
    insert_into_db(coverage_data)
    gen_html(abs_dest)

if __name__ == "__main__":
    main()
