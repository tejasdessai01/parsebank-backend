from flask import Flask, request, send_file, jsonify
import pdfplumber
import pandas as pd
import tempfile
import os
import re

app = Flask(__name__)

@app.route('/parse', methods=['POST'])
def parse_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    print("File received:", file.filename)

    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    file.save(temp_pdf.name)

    data = []
    try:
        with pdfplumber.open(temp_pdf.name) as pdf:
            raw_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

            # Basic validation: look for typical bank keywords
            if not re.search(r'(account|transaction|statement|balance)', raw_text, re.IGNORECASE):
                return jsonify({"error": "This file does not appear to be a valid bank statement."}), 400

            for page in pdf.pages:
                table = page.extract_table()
                if not table:
                    continue
                for row in table[1:]:
                    if len(row) >= 5:
                        data.append({
                            "Date": row[0],
                            "Description": row[1],
                            "Debit": row[2],
                            "Credit": row[3],
                            "Balance": row[4],
                        })

        if not data:
            return jsonify({"error": "No transactions found in the uploaded file."}), 400

        df = pd.DataFrame(data)
        df["Debit"] = df["Debit"].fillna("")
        df["Credit"] = df["Credit"].fillna("")

        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        df.to_excel(output_file.name, index=False)

        print("Returning Excel:", output_file.name)
        return send_file(output_file.name, as_attachment=True, download_name="parsed_statement.xlsx")

    finally:
        os.unlink(temp_pdf.name)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
