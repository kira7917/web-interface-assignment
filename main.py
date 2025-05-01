import csv
import smtplib
import os
from email.mime.text import MIMEText
from flask import Flask, request, send_file, render_template
from werkzeug.utils import secure_filename
from email.mime.multipart import MIMEMultipart
from collections import defaultdict
import datetime

def read_csv(filename):
    """
    Reads a CSV file and returns its contents as a list of lists.

    Args:
        filename: The path to the CSV file.

    Returns:
        A list of lists where each inner list represents a row in the CSV,
        or None if an error occurs.
    """
    data = []
    try:
        with open(filename, 'r') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                data.append(row)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    return data

UPLOAD_FOLDER = 'uploads'

def delete_row(filename, restaurant_name, date_to_delete):
    """
    Deletes a row from a CSV file based on restaurant name and date.

    Args:
        filename: The path to the CSV file.
        restaurant_name: The name of the restaurant to delete.
        date_to_delete: The date of the row to delete.

    Returns:
        A success or error message.
    """
    filename = os.path.join(UPLOAD_FOLDER, filename)
    try:
        with open(filename, 'r', newline='', encoding='utf-8') as file:
          reader = csv.DictReader(file)
          rows = list(reader)
    except FileNotFoundError:
        return f"Error: File '{filename}' not found."
    except FileNotFoundError:
        return f"Error: File '{filename}' not found."
    except Exception as e:
        return f"An error occurred: {e}"
    header_row = reader.fieldnames
    restaurant_name_index = -1
    order_date_index = -1
    
    if header_row:
      restaurant_name_index = header_row.index('Restaurant Name') if 'Restaurant Name' in header_row else -1
      order_date_index = header_row.index('Order Date') if 'Order Date' in header_row else -1

    if restaurant_name_index == -1 or order_date_index == -1:
        return "Error: Restaurant Name or Order Date column not found."
    row_to_delete = [i for i, row in enumerate(rows) if row['Restaurant Name'].strip().lower() == restaurant_name.strip().lower() and row['Order Date'].strip() == date_to_delete.strip()]

    if row_to_delete:
      deleted_row = rows.pop(row_to_delete[0])
      with open(filename, 'w', newline='', encoding='utf-8') as file:
          writer = csv.DictWriter(file, fieldnames=header_row)
          writer.writeheader()
          writer.writerows(rows)
      return f"Data for restaurant '{deleted_row['Restaurant Name']}' on '{deleted_row['Order Date']}' deleted successfully."
    return f"There is no data for restaurant '{restaurant_name}' on '{date_to_delete}'."
def download_csv(output_file, data):
    header = ["Order Date","ONDC Order ID","Restaurant Name","Restaurant ID","Locality","Order Status","Order Total","Copay","Copay Amount","Net Bill Value","Total Container Charge","Total GST","Commission %","GST on commission %","TCS","TDS","GF Platform Fee","GST on GF Platform Fee","Self Delivery Charges","Delivery Discount","Total Payable to Merchant"]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=header)  # Use DictWriter
        writer.writeheader()  # Write the header row
        for row in data:
          writer.writerow(row)  # Write each row

def send_email(message, to_email, subject):
    """
    Sends an email to the specified recipient.

    Args:
        message: The body of the email.
        to_email: The recipient's email address.
        subject: The subject of the email.
    """
    from_email = "mann79177917@gmail.com"  # Replace with your email
    from_password = "wbilnbgvbejofqib"  # Replace with your password

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(message, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)  # Replace with your email server settings if not using gmail
        server.starttls()
        server.login(from_email, from_password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"An error occurred while sending the email: {e}")
        raise

def daily_summary(filename):
    filename = os.path.join(UPLOAD_FOLDER, filename)
    """
    Generates a daily summary from the GFF_March_2025.csv file.

    Args:
        filename: The name of the CSV file.

    Returns:
        A string containing the daily summary.
    """
    data = read_csv(filename)
    if data is None or len(data) < 2:  #check if file was read and if there are data rows
      return "Error: no data found"

    
    summary = defaultdict(float)
    header = {h.strip().lower():i for i,h in enumerate(data[0])} #get header and clean it
    order_date_index = -1
    amount_index = -1
    restaurant_index = -1    
    if 'order date' in header:
      order_date_index = header.index('order date')
    if 'total payable to merchant' in header:
      amount_index = header.index('total payable to merchant')
    if 'restaurant name' in header:
      restaurant_index = header.index('restaurant name')

    if order_date_index == -1:
        return "Error: Order Date column not found."
    if amount_index == -1:
        return "Error: Total payable to merchant column not found."
    if restaurant_index == -1:
        return "Error: Restaurant Name column not found."

    for row in data[1:]:  # Skip the header row
        if len(row) > max(order_date_index,amount_index,restaurant_index):
            try:
                date_str = row[order_date_index]
                date_obj = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                date = date_obj.date().isoformat()
                amount = float(row[amount_index])
                summary[date] += amount
            except ValueError:
                return "Error: Amount not a number."

    summary_string = ""
    for date, total in summary.items():
        summary_string += f"Date: {date}, Total Amount: {total}\n"

    return summary_string

app = Flask(__name__, static_folder='src')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Handles the file upload.
    """
    if 'file' not in request.files:
        return 'No file part in the request'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        filename = secure_filename(file.filename)
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
          os.makedirs(app.config['UPLOAD_FOLDER'])
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return 'File successfully uploaded'
    return "File upload failed"

def display_data(filename, restaurant, date, page=1):
    """
    Reads a CSV file, filters data for a specific restaurant and date,
    and formats the filtered data in an HTML table.
    Limits the number of rows displayed to 10 per page.

    Args:
        filename: The name of the CSV file.
        restaurant: The name of the restaurant to filter by.
        date: The date to filter by.
        page: The page number to display.

    Returns:
        An HTML string representing the table or an error message.
    """
    try:
        filename = os.path.join(UPLOAD_FOLDER, filename)
        with open(filename, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            data = list(reader)
    except FileNotFoundError:
        return f"Error: File '{filename}' not found."
    except Exception as e:
        return f"Error reading data: {e}"

    filtered_data = []
    # Filtering data based on restaurant and date
    for row in data:
      if not isinstance(row,dict):
        continue
      if 'Order Date' not in row:
        continue
      if 'Restaurant Name' not in row:
        continue
      row_date_str = row['Order Date']
      row_date_obj = datetime.datetime.fromisoformat(row_date_str.replace("Z", "+00:00"))
      row_date = row_date_obj.date().isoformat()
      if row['Restaurant Name'].strip().lower() == restaurant.strip().lower() and row_date == date:
        filtered_data.append(row)
    
    
    total_rows = len(filtered_data)
    rows_per_page = 10
    max_page = (total_rows + rows_per_page - 1) // rows_per_page
    
    start_index = (page - 1) * 10
    end_index = min(start_index + 10, total_rows)
    rows_to_display = filtered_data[start_index:end_index]

    if page > max_page or total_rows == 0:
        return "<table border='1'></table>"

    html_table = "<table class='table'>"
    html_table += "<thead class='thead-dark'><tr>" + "".join(f"<th>{header}</th>" for header in data[0].keys()) + "</tr></thead>"
    html_table += "<tbody>"

    for row in rows_to_display:
        html_table += "<tr>" + "".join(f"<td>{row[key]}</td>" for key in data[0].keys()) + "</tr>"

    html_table += "</tbody></table>"


    if total_rows == 0 :
        return f"No data found for restaurant '{restaurant}' on date '{date}'."    

    if page < max_page:
      html_table += f"<button onclick='changePage({page + 1})'>Next</button>"
    if page > 1:
      html_table += f"<button onclick='changePage({page - 1})'>Previous</button>"



    return html_table

@app.route('/display')
def display():
    """
    Handles the display of data for a specific restaurant and date.
    """
    restaurant = request.args.get('restaurant')
    date = request.args.get('date')
    filename = "GFF_March_2025.csv"
    page = int(request.args.get('page', 1))  # Get the page number from the request, default to 1
    return display_data(filename, restaurant, date, page)

@app.route('/email')
def email():
    """
    Sends an email with the daily summary.
    """
    to_email = request.args.get('email')
    filename = "GFF_March_2025.csv"
    message = daily_summary(filename)
    send_email(message, to_email, "Daily Summary")
    return "Email sent"

@app.route('/download')
def download():
    """
    Downloads a CSV file with data filtered by restaurant and date.
    """
    restaurant = request.args.get('restaurant')
    date = request.args.get('date')
    filename = "GFF_March_2025.csv"
    data = read_csv(filename)
    if data is None:
        return "Error reading data."

    header = {h.strip().lower():i for i,h in enumerate(data[0])} #get header and clean it
    restaurant_index = header.get('restaurant name',-1) 
    order_date_index = header.get('order date',-1)
    if restaurant_index == -1 or order_date_index == -1:
      return "Error: Restaurant Name or Order Date column not found."

    filtered_data = []
    for row in data[1:]:
        try:
          row_date_str = row[order_date_index]
          row_date_obj = datetime.datetime.fromisoformat(row_date_str.replace("Z", "+00:00"))
          row_date = row_date_obj.date().isoformat()
          if row[restaurant_index].strip().lower() == restaurant.strip().lower() and row_date == date:
            filtered_data.append(row)
        except ValueError:
          return "Error: Invalid date format."
          
    if not filtered_data:
        return "No data found for the specified criteria"
    
    output_file = "download.csv"
    download_csv(output_file, filtered_data)
    return send_file(output_file, as_attachment=True)

@app.route('/delete')
def delete():
    """
    Deletes data from the CSV file for a specific restaurant.
    """
    restaurant = request.args.get('restaurant')
    date = request.args.get('date')
    filename = "GFF_March_2025.csv"    
    return delete_row(filename, restaurant,date)

if __name__ == "__main__":
    app.run(debug=True)