import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os
from fpdf import FPDF
import base64

st.set_page_config(page_title="💰 Advanced Budget Tracker", layout="centered")

# -- Logo and Title --
st.image("https://i.imgur.com/jNNT4LE.png", width=80)
st.markdown(
    '''
    <h1 style='text-align: center; color: #2E8B57;'>💼 Personal Budget Tracker</h1>
    <p style='text-align: center; font-size:18px;'>Track, Analyze, and Take Charge of Your Finances</p>
    <hr style='border-top: 1px solid #bbb;'/>
    ''',
    unsafe_allow_html=True
)

# --- USER LOGIN ---
st.sidebar.header("👤 User Login")
username = st.sidebar.text_input("Enter your name to continue")

if not username:
    st.warning("Please enter your name in the sidebar to proceed.")
    st.stop()

filename = f"{username.lower().replace(' ', '_')}_transactions.csv"
users_file = "users.txt"

# Save unique users for developer-only tracking
if not os.path.exists(users_file):
    with open(users_file, "w") as f:
        f.write("")

with open(users_file, "r") as f:
    users = [line.strip() for line in f.readlines()]
if username not in users:
    with open(users_file, "a") as f:
        f.write(f"{username}\n")

# --- LOAD USER DATA ---
if os.path.exists(filename):
    df = pd.read_csv(filename)
else:
    df = pd.DataFrame(columns=["Date", "Type", "Category", "Amount"])

if not df.empty:
    df["Date"] = pd.to_datetime(df["Date"])

st.session_state["df"] = df

# --- ADD NEW TRANSACTION ---
with st.form("transaction_form"):
    st.subheader("➕ Add New Transaction")
    t_type = st.selectbox("Type", ["Income", "Expense"])
    category = st.text_input("Category (e.g., Rent, Food, Salary)")
    amount = st.number_input("Amount", min_value=0.0, format="%.2f")
    date_input = st.date_input("Transaction Date", value=datetime.today().date())
    submitted = st.form_submit_button("Add")

    if submitted:
        if category and amount > 0:
            new_data = {
                "Date": pd.to_datetime(str(date_input)),
                "Type": t_type,
                "Category": category.strip().title(),
                "Amount": amount
            }
            st.session_state["df"] = pd.concat([st.session_state["df"], pd.DataFrame([new_data])], ignore_index=True)
            st.session_state["df"].to_csv(filename, index=False)
            st.success(f"{t_type} of Rs. {amount:.2f} added under '{category}'")
            st.rerun()
        else:
            st.warning("Please enter valid details.")
# --- EDIT / DELETE TRANSACTIONS ---
df = st.session_state["df"]

if not df.empty:
    st.subheader("✏️ Edit or Delete Transactions")
    edited_index = st.selectbox(
        "Select a transaction to edit/delete",
        df.index,
        format_func=lambda x: f"{df.at[x, 'Date'].date()} – {df.at[x, 'Type']} – {df.at[x, 'Category']} – Rs. {df.at[x, 'Amount']:.2f}"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑 Delete Transaction"):
            df = df.drop(index=edited_index).reset_index(drop=True)
            df.to_csv(filename, index=False)
            st.success("Transaction deleted.")
            st.rerun()

    with col2:
        with st.expander("✏️ Edit Transaction Details"):
            new_type = st.selectbox("New Type", ["Income", "Expense"], index=["Income", "Expense"].index(df.at[edited_index, "Type"]))
            new_category = st.text_input("New Category", value=df.at[edited_index, "Category"])
            new_amount = st.number_input("New Amount", value=float(df.at[edited_index, "Amount"]), min_value=0.0, format="%.2f")
            new_date = st.date_input("New Date", value=df.at[edited_index, "Date"].date())
            if st.button("✅ Save Changes"):
                df.at[edited_index, "Type"] = new_type
                df.at[edited_index, "Category"] = new_category.strip().title()
                df.at[edited_index, "Amount"] = new_amount
                df.at[edited_index, "Date"] = pd.to_datetime(str(new_date))
                df.to_csv(filename, index=False)
                st.success("Transaction updated.")
                st.rerun()

# --- SUMMARY & CHARTS ---
if not df.empty:
    st.subheader("📋 Transaction History")
    st.dataframe(df.sort_values("Date"), use_container_width=True)

    income = df[df["Type"] == "Income"]["Amount"].sum()
    expenses = df[df["Type"] == "Expense"]["Amount"].sum()
    balance = income - expenses

    st.subheader("📊 Financial Summary")
    st.markdown(f"**💰 Total Income:** Rs. {income:.2f}")
    st.markdown(f"**💸 Total Expenses:** Rs. {expenses:.2f}")
    st.markdown(f"**🧾 Current Balance:** Rs. {balance:.2f}")

    # Pie Chart
    st.subheader("📌 Category-wise Expense Breakdown")
    pie_data = df[df["Type"] == "Expense"].groupby("Category")["Amount"].sum()
    if not pie_data.empty:
        fig1, ax1 = plt.subplots()
        ax1.pie(pie_data, labels=pie_data.index, autopct="%1.1f%%", startangle=90)
        ax1.axis("equal")
        st.pyplot(fig1)
    else:
        st.info("No expense data available.")

    # Line Chart
    st.subheader("📈 Financial Trends Over Time")
    trend = df.groupby(["Date", "Type"])["Amount"].sum().unstack().fillna(0)
    st.line_chart(trend)

    # --- PDF REPORT ---
    st.subheader("📥 Download Report")

    def generate_pdf(dataframe, total_income, total_expenses, balance_amt):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, f"{username.title()}'s Budget Report", ln=True, align="C")
        pdf.ln(10)

        pdf.cell(200, 10, f"Total Income: Rs. {total_income:.2f}", ln=True)
        pdf.cell(200, 10, f"Total Expenses: Rs. {total_expenses:.2f}", ln=True)
        pdf.cell(200, 10, f"Current Balance: Rs. {balance_amt:.2f}", ln=True)
        pdf.ln(10)

        pdf.set_font("Arial", size=10)
        pdf.cell(40, 10, "Date", border=1)
        pdf.cell(30, 10, "Type", border=1)
        pdf.cell(60, 10, "Category", border=1)
        pdf.cell(30, 10, "Amount", border=1)
        pdf.ln()

        for _, row in dataframe.iterrows():
            pdf.cell(40, 10, str(row["Date"].date()), border=1)
            pdf.cell(30, 10, row["Type"], border=1)
            pdf.cell(60, 10, row["Category"], border=1)
            pdf.cell(30, 10, f"Rs. {row['Amount']:.2f}", border=1)
            pdf.ln()

        output_path = f"{username.lower().replace(' ', '_')}_budget_report.pdf"
        pdf.output(output_path)
        return output_path

    if st.button("⬇️ Generate PDF Report"):
        report_path = generate_pdf(df, income, expenses, balance)
        with open(report_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="{report_path}">📄 Click here to download your report</a>'
            st.markdown(href, unsafe_allow_html=True)

else:
    st.info("No transactions recorded yet.")
