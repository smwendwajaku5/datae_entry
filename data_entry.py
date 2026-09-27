import tkinter as tk
from tkinter import messagebox, ttk
import os

import pyodbc


SQL_SERVER = os.getenv("DATA_ENTRY_SQL_SERVER", r"localhost\SQLEXPRESS")
SQL_DATABASE = os.getenv("DATA_ENTRY_SQL_DATABASE", "DataEntryDB")
SQL_USERNAME = os.getenv("DATA_ENTRY_SQL_USERNAME", "")
SQL_PASSWORD = os.getenv("DATA_ENTRY_SQL_PASSWORD", "")
SQL_DRIVER = os.getenv("DATA_ENTRY_SQL_DRIVER", "ODBC Driver 18 for SQL Server")
TABLE_NAME = "dbo.Contacts"
SQL_CONNECTION_TIMEOUT = 5


class DataEntryApp:
	def __init__(self, window: tk.Tk) -> None:
		self.window = window
		self.window.title("Contacts Data Entry")
		self.window.geometry("1000x650")
		self.window.minsize(850, 550)
		self.selected_id: int | None = None

		self.first_name = tk.StringVar()
		self.last_name = tk.StringVar()
		self.phone = tk.StringVar()
		self.email = tk.StringVar()
		self.search_text = tk.StringVar()

		self.build_interface()
		self.load_records()

	def connection_string(self) -> str:
		authentication = (
			f"UID={SQL_USERNAME};PWD={SQL_PASSWORD};"
			if SQL_USERNAME
			else "Trusted_Connection=yes;"
		)
		return (
			f"DRIVER={{{SQL_DRIVER}}};SERVER={SQL_SERVER};"
			f"DATABASE={SQL_DATABASE};{authentication}TrustServerCertificate=yes;"
		)

	def get_connection(self) -> pyodbc.Connection:
		return pyodbc.connect(self.connection_string(), timeout=SQL_CONNECTION_TIMEOUT)

	def build_interface(self) -> None:
		form = ttk.LabelFrame(self.window, text="Contact details", padding=12)
		form.pack(fill="x", padx=12, pady=(12, 6))

		fields = [
			("First name", self.first_name, 0, 0),
			("Last name", self.last_name, 0, 2),
			("Phone", self.phone, 1, 0),
			("Email", self.email, 1, 2),
		]
		for label, variable, row, column in fields:
			ttk.Label(form, text=label).grid(row=row, column=column, sticky="w", padx=6, pady=6)
			ttk.Entry(form, textvariable=variable, width=32).grid(
				row=row, column=column + 1, sticky="ew", padx=6, pady=6
			)
		form.columnconfigure(1, weight=1)
		form.columnconfigure(3, weight=1)

		address_frame = ttk.Frame(form)
		address_frame.grid(row=2, column=0, columnspan=4, sticky="ew", padx=6, pady=6)
		ttk.Label(address_frame, text="Address").pack(side="left", padx=(0, 12))
		self.address = tk.Text(address_frame, height=3, width=70)
		self.address.pack(side="left", fill="x", expand=True)

		actions = ttk.Frame(self.window)
		actions.pack(fill="x", padx=12, pady=6)
		ttk.Button(actions, text="Save new", command=self.save_record).pack(side="left", padx=4)
		ttk.Button(actions, text="Update selected", command=self.update_record).pack(side="left", padx=4)
		ttk.Button(actions, text="Delete selected", command=self.delete_record).pack(side="left", padx=4)
		ttk.Button(actions, text="Clear form", command=self.clear_form).pack(side="left", padx=4)

		search = ttk.Frame(self.window)
		search.pack(fill="x", padx=12, pady=6)
		ttk.Label(search, text="Search").pack(side="left", padx=(0, 8))
		search_entry = ttk.Entry(search, textvariable=self.search_text, width=35)
		search_entry.pack(side="left")
		search_entry.bind("<Return>", lambda _event: self.load_records())
		ttk.Button(search, text="Search", command=self.load_records).pack(side="left", padx=6)
		ttk.Button(search, text="Show all", command=self.show_all).pack(side="left")

		table_frame = ttk.Frame(self.window)
		table_frame.pack(fill="both", expand=True, padx=12, pady=(6, 12))
		columns = ("id", "first_name", "last_name", "phone", "email", "address")
		self.table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
		headings = {
			"id": "ID", "first_name": "First name", "last_name": "Last name",
			"phone": "Phone", "email": "Email", "address": "Address",
		}
		widths = {"id": 55, "first_name": 120, "last_name": 120, "phone": 120, "email": 190, "address": 240}
		for column in columns:
			self.table.heading(column, text=headings[column])
			self.table.column(column, width=widths[column], anchor="w")
		self.table.bind("<<TreeviewSelect>>", self.select_record)
		scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
		self.table.configure(yscrollcommand=scrollbar.set)
		self.table.pack(side="left", fill="both", expand=True)
		scrollbar.pack(side="right", fill="y")

	def values_from_form(self) -> tuple[str, str, str, str, str] | None:
		values = (
			self.first_name.get().strip(), self.last_name.get().strip(),
			self.phone.get().strip(), self.email.get().strip(),
			self.address.get("1.0", "end").strip(),
		)
		if not values[0] or not values[1]:
			messagebox.showwarning("Missing information", "First name and last name are required.")
			return None
		return values

	def save_record(self) -> None:
		values = self.values_from_form()
		if values is None:
			return
		try:
			with self.get_connection() as connection:
				connection.execute(
					f"INSERT INTO {TABLE_NAME} (first_name, last_name, phone, email, address) VALUES (?, ?, ?, ?, ?)",
					values,
				)
				connection.commit()
			self.clear_form()
			self.load_records()
			messagebox.showinfo("Saved", "The contact was saved.")
		except pyodbc.Error as error:
			self.show_database_error(error)

	def update_record(self) -> None:
		if self.selected_id is None:
			messagebox.showwarning("No selection", "Select a contact before updating it.")
			return
		values = self.values_from_form()
		if values is None:
			return
		try:
			with self.get_connection() as connection:
				connection.execute(
					f"UPDATE {TABLE_NAME} SET first_name=?, last_name=?, phone=?, email=?, address=? WHERE id=?",
					(*values, self.selected_id),
				)
				connection.commit()
			self.clear_form()
			self.load_records()
			messagebox.showinfo("Updated", "The contact was updated.")
		except pyodbc.Error as error:
			self.show_database_error(error)

	def delete_record(self) -> None:
		if self.selected_id is None:
			messagebox.showwarning("No selection", "Select a contact before deleting it.")
			return
		if not messagebox.askyesno("Confirm delete", "Delete the selected contact?"):
			return
		try:
			with self.get_connection() as connection:
				connection.execute(f"DELETE FROM {TABLE_NAME} WHERE id=?", (self.selected_id,))
				connection.commit()
			self.clear_form()
			self.load_records()
		except pyodbc.Error as error:
			self.show_database_error(error)

	def load_records(self) -> None:
		search = self.search_text.get().strip()
		query = f"SELECT id, first_name, last_name, phone, email, address FROM {TABLE_NAME}"
		parameters: tuple[str, ...] = ()
		if search:
			query += " WHERE first_name LIKE ? OR last_name LIKE ? OR phone LIKE ? OR email LIKE ?"
			pattern = f"%{search}%"
			parameters = (pattern, pattern, pattern, pattern)
		query += " ORDER BY id DESC"
		try:
			with self.get_connection() as connection:
				rows = connection.execute(query, parameters).fetchall()
			for item in self.table.get_children():
				self.table.delete(item)
			for row in rows:
				self.table.insert("", "end", values=tuple(row))
		except pyodbc.Error as error:
			self.show_database_error(error)

	def select_record(self, _event: tk.Event) -> None:
		selection = self.table.selection()
		if not selection:
			return
		values = self.table.item(selection[0], "values")
		self.selected_id = int(values[0])
		self.first_name.set(values[1])
		self.last_name.set(values[2])
		self.phone.set(values[3])
		self.email.set(values[4])
		self.address.delete("1.0", "end")
		self.address.insert("1.0", values[5])

	def clear_form(self) -> None:
		self.selected_id = None
		self.first_name.set("")
		self.last_name.set("")
		self.phone.set("")
		self.email.set("")
		self.address.delete("1.0", "end")
		for item in self.table.selection():
			self.table.selection_remove(item)

	def show_all(self) -> None:
		self.search_text.set("")
		self.load_records()

	@staticmethod
	def show_database_error(error: pyodbc.Error) -> None:
		messagebox.showerror(
			"Database error",
			"Could not connect to or use the SQL Server database.\n\n"
			f"Check the connection settings and table name.\n\n{error}",
		)


if __name__ == "__main__":
	root = tk.Tk()
	DataEntryApp(root)
	root.mainloop()
