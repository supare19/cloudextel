import frappe
from frappe.utils.data import today,getdate,get_datetime,get_datetime_str,date_diff
from frappe.utils import get_url,get_absolute_url
from frappe.utils import get_html_format
from frappe import sendmail
import datetime




def get_table_html():
    return """
                        <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <style>
                                /* Add your CSS styles here */
                                table {
                                    border-collapse: collapse;
                                    width: 100%;
                                }

                                th, td {
                                    border: 1px solid #dddddd;
                                    text-align: left;
                                    padding: 8px;
                                }

                                th {
                                    background-color: #f2f2f2;
                                }
                            </style>
                        </head>
                        <body> 
                        """


# <h2>Your Table Heading</h2>
#     <table>
#         <tr>
#             <th>Header 1</th>
#             <th>Header 2</th>
#             <th>Header 3</th>
#         </tr>
#         <tr>
#             <td>Data 1</td>
#             <td>Data 2</td>
#             <td>Data 3</td>
#         </tr>
#         <tr>
#             <td>Data 4</td>
#             <td>Data 5</td>
#             <td>Data 6</td>
#         </tr>
#     </table>
# </body>
# </html>

@frappe.whitelist()
def on_comment_add(doc, method):
    # Check if the comment is related to the TaskManager document
    if doc.reference_doctype == "Task Manager" and doc.reference_name:
        # Your custom logic for when a comment is added to TaskManager
        print(frappe.as_json(doc))
        doca = frappe.get_doc('Task Manager',doc.reference_name)
        url = doca.get_url()
        c_Data = frappe.db.sql("""
                            
                            SELECT * FROM `tabComment`
                            WHERE reference_doctype = %(doc)s
                            AND reference_name = %(name)s
                            AND comment_type IN %(ctypes)s 
                               order by creation desc
                        """, {'doc': 'Task Manager', 'name': doca.name, 'ctypes': ('Comment', 'Workflow')}, as_dict=True)

            # Construct HTML content
        html_content = """
        <html>
        <head>
            <style>
                /* Add your CSS styles here */
                table {
                    border-collapse: collapse;
                    width: 100%;
                }

                th, td {
                    border: 1px solid #dddddd;
                    text-align: left;
                    padding: 8px;
                }

                th {
                    background-color: #f2f2f2;
                }
            </style>
        </head>
        <body>"""+ f"""
            <h1> Task - {doca.task_name} </h1>
            <h4> Description - {doca.task_description} </h4>
            <h4> Start Date - {doca.start_date.strftime("%d-%b-%Y")} </h4>
            <h4> Due Date - {doca.due_date.strftime("%d-%b-%Y")} </h4>
            <h4> Link - <a href={url}>{url}</a></h4>

            <table>
                <tr>
                    <th>Index</th>
                    <th>Comment By</th>
                    <th>Content</th>
                    <th>Time</th>
                </tr>
        """

        for index, row in enumerate(c_Data, start=1):
            html_content += f"""
                <tr>
                    <td>{index}</td>
                    <td>{ row.get('owner') +" Changes Status to" if row.get('comment_by',None) is None else row.get('comment_by') }</td>
                    <td>{row.get('content', '')}</td>
                    <td>{row.get('creation').strftime("%d-%b-%Y %I.%M %p")}</td>
                </tr>
            """

        html_content += """
            </table>
        </body>
        </html>
        """
        print(html_content)

        if doca.reply is None:
            subject = f"Task - {doca.task_name} Trails"
            recipients = [doca.task_owner] + [i.user for i in doca.assign_to]
            cc_recipients = [recipients[0]] + recipients[2:]
            frappe.sendmail(recipients=[recipients[1]], subject=subject, message=html_content,cc=",".join(cc_recipients))
            print('Email Success..!!')
            doca.reply = 1
            doca.save()
            frappe.db.commit()
        else:
            default_sender = frappe.get_value('Email Account', {'default_outgoing': 1}, 'email_id')
            subject = f"RE: Task - {doca.task_name} Trails"
            recipients = [doca.task_owner] + [i.user for i in doca.assign_to]
            cc_recipients = [recipients[0]] + recipients[2:]
            frappe.sendmail(recipients=[recipients[1]], reply_to=default_sender,cc=", ".join(cc_recipients),bcc=", ".join(cc_recipients), subject=subject, message=html_content,reference_doctype='Task Manager',reference_name=doca.name)
            print('Email Success..!!')

        

        # # Now you can use `formatted_html` in your email sending function
        # print(formatted_html,"----")




def check_workflow_for_tm(doc,method):
    old_doc = doc.get_doc_before_save()
    if not old_doc:
        return
    if old_doc.get('status') in ['Assigned','Hold'] and doc.get('status') == 'Closed':
        docs = frappe.db.sql("""Select name,task_name,task_description from `tabTask Manager` where status != 'Closed' and next_task_link=%(name)s""",{'name':doc.name},as_dict=1)
        if len(docs):
            print(docs,",".join([i['task_name'] for i in docs]))
            frappe.throw("Current Task - <b>{}</b> Not Allowed To Mark As Closed.<br> Please Complete its Dependants Task - <b>{}</b>".format( f"<a href={doc.get_url()}>" + "" + doc.task_name +"</a>"," , ".join([f"<a href={get_absolute_url('Task Manager',i['name'])}>" + i['task_name'] +"</a>" for i in docs])))
            frappe.db.rollback()
        else:  
            frappe.db.sql("""update `tabTask Manager` set closure_date = %(date)s  where name =%(name)s""",{'date':getdate(today()),'name':doc.name})
            doc.reload()




def send_email_notification(task,all_dependant_task_data,due_date_cross=False):
    doc_data = [i[2]['doc'] for i in all_dependant_task_data]
    content = f"""<h2>{task['task_name']} - Pending Task Hierarchy Summary </h2>
            <table>
             <tr>
                <th>Sr.</th>
                <th>Task Name</th>
                <th>Task Start Date</th>
                <th>Task End Date</th>
                <th>Task Closure Date</th>
                <th>Task Lag (Days)</th>
                <th>Next Dependant Task</th>
                <th>Status </th>
            </tr>
        """
    index = 1  
    for _task_li in doc_data:
        content += f"""<tr><td> {index} </td>
                       <td> {_task_li['task_name']}</td> 
                       <td> {_task_li['start_date'].strftime("%d-%b-%Y")}</td> 
                       <td> {_task_li['due_date'].strftime("%d-%b-%Y")}</td> 
                       <td> {_task_li['closure_date'].strftime('%d-%b-%Y') if _task_li.get('closure_date') else "-" }</td> 
                        <td> {_task_li['age']  if _task_li['status'] == 'Closed' and _task_li.get('closure_date') else 0 }</td> 
                        <td> {_task_li['next_task_name'] if _task_li.get('next_task_name') else "-"}</td>
                        <td> {_task_li['status']}</td> 
                        </tr> 
                    """
        index +=1
    content += """</table></body></html>"""
    if due_date_cross:
        lag = date_diff(today(),task['due_date'])
        task_master_email_utils(2,frappe.get_doc('Task Manager',task['name']),content,lag)        
    else:
        t = frappe.get_doc('Task Manager',task['name'])
        task_master_email_utils(1,t,content)        

def perform_the_operation_on_data(task_data_tuple,t_D):
    for task in task_data_tuple:
        if task[2]['status'].strip().lower() != 'closed':
            if getdate(task[2]['doc']['due_date']) < getdate(today()):
                send_email_notification(task[2]['doc'],task_data_tuple,True)
            else:
                send_email_notification(task[2]['doc'],task_data_tuple)   
            break



def get_converted_list_of_tasks(task_dict):
    #data = {'a': {'level': 1, 'status': '', 'doc': {}}, 'b': {'level': 3, 'status': '', 'doc': {}}, 'c': {'level': 2, 'status': '', 'doc': {}}}
    sorted_data = sorted(task_dict.items(), key=lambda x: x[1]['level'], reverse=True)
    # It will return Tuple with key,level,data
    return [(key, value.pop('level'), value) for key, value in sorted_data]



# def get_closed_hierarchy_tickets(id,li):
#     d = frappe.get_all('Task Manager',fields=["*"],filters={'next_task_link':id,'status':'Closed'})
#     if len(d) == 0:
#         return li
#     elif len(d) == 1:
#         li.insert(0,d[0])
#         return get_closed_hierarchy_tickets(d[0]['name'],li)
#     elif len(d) > 1:
#         for i in d:
#             li.insert(0,i)  
#             return get_closed_hierarchy_tickets(i['name'],li)  


    



@frappe.whitelist()
def task_manager_notification_job():
    tasks_list = frappe.get_all("Task Manager",fields=["*"],filters=[['next_task_link','=',''],['status','!=','Closed']])
    if len(tasks_list):
        for task in tasks_list:
            ts ={}
            level = 1 
            ts[task['name']] = {'level':1,'status':task['status'],'doc':task} 
            perform_hierachy_level_operations(task,ts,level)
            task_array_with_frequency = get_converted_list_of_tasks(ts)
            closed_tickets_data = []
            # if len(ts) > 1 and task_array_with_frequency[0][2]['status'].lower() == 'closed':
            #     get_closed_hierarchy_tickets(task_array_with_frequency[0][0],closed_tickets_data) 
            perform_the_operation_on_data(task_array_with_frequency,closed_tickets_data)


def perform_hierachy_level_operations(task,task_sequence,level):
    _next_task = frappe.get_all('Task Manager',fields=["*"],filters={'next_task_link':task['name']})
    if len(_next_task) == 1:
        if _next_task[0]['status'].strip() == 'Closed':
            if task_sequence.get(_next_task[0]['name']) is None:
                level = level + 1
                task_sequence[_next_task[0]['name']] = {
                    'level':level,
                    'status':'Closed',
                    'doc':_next_task[0]
                }
                return
        elif _next_task[0]['status'].strip() == 'Assigned':
            if task_sequence.get(_next_task[0]['name']) is None:
                level = level + 1
                task_sequence[_next_task[0]['name']] = {
                    'level':level,
                    'status':'Assigned',
                    'doc':_next_task[0]
                }
                perform_hierachy_level_operations(_next_task[0],task_sequence,level)        

        elif _next_task[0]['status'].strip() not in ['Closed','Assigned']:
            if task_sequence.get(_next_task[0]['name']) is None:
                level = level + 1
                task_sequence[_next_task[0]['name']] = {
                    'level':level,
                    'status':_next_task[0]['status'],
                    'doc':_next_task[0]
                }
                perform_hierachy_level_operations(_next_task[0],task_sequence,level)         
    elif len(_next_task)>1:
        for _ntask in _next_task:
            if _ntask['status'].strip().lower() == 'closed':
                if task_sequence.get(_ntask['name']) is None:
                    level = level + 1
                    task_sequence[_ntask['name']] = {
                        'level':level,
                        'status':_ntask['status'],
                        'doc':_ntask
                    }
                    return
            elif _ntask['status'].strip().lower() == 'assigned':
                if task_sequence.get(_ntask['name']) is None:
                    level = level + 1
                    task_sequence[_ntask['name']] = {
                        'level':level,
                        'status':_ntask['status'],
                        'doc':_ntask
                    }
                    perform_hierachy_level_operations(_ntask,task_sequence,level)
            elif _ntask['status'].strip().lower() not in ['Closed','Assigned']:
                if task_sequence.get(_ntask['name']) is None:
                    level = level + 1
                    task_sequence[_ntask['name']] = {
                        'level':level,
                        'status':_ntask['status'],
                        'doc':_ntask
                    }
                    perform_hierachy_level_operations(_ntask,task_sequence,level) 

    else:
        return                 


def task_master_email_utils(etype,task,content,lag=0):
    try:
        if etype == 1:
            assign_to = [i.user for i in task.assign_to]
            subject = f"Task - {task.task_name} Pending (Due Date - {task.due_date})"
            template = frappe.get_doc('Email Template','Task Manager - Pending Near Due').response
            message = template.format(assign=",".join(assign_to),
                            name=task.task_name,
                            desc=task.task_description,
                            due_date=task.due_date.strftime("%d-%b-%Y"))
            recipients = assign_to
            message += content
            cc = task.task_owner
            message  = get_table_html() + message
            print(message,recipients,subject,cc)
            frappe.sendmail(recipients=recipients,subject=subject,message=message,cc=cc)
        elif etype== 2:
            assign_to = [i.user for i in task.assign_to]
            subject = f"Task - {task.task_name} Pending (Exceeds Due Date - {task.due_date})"
            template = frappe.get_doc('Email Template','Task Manager - Post Due Date').response
            message = template.format(assign=",".join(assign_to),
                            name=task.task_name,
                            desc=task.task_description,
                            due_date=task.due_date.strftime("%d-%b-%Y"),lag=lag)
            recipients = assign_to
            message += content
            cc = task.task_owner
            frappe.sendmail(recipients=recipients,subject=subject,message=message,cc=cc)  
        elif  etype == 3:
            assign_to = [i.user for i in task.assign_to]
            subject = f"Task - {task.task_name} Pending (Exceeds Due Date - {task.due_date})"
            template = frappe.get_doc('Email Template','Task Manager - Post Due Date Parent').response
            message = template.format(assign=",".join(assign_to),
                            name=task.task_name,
                            desc=task.task_description,
                            due_date=task.due_date.strftime("%d-%b-%Y"),lag=lag)
            recipients = assign_to
            message += content
            cc = task.task_owner
            frappe.sendmail(recipients=recipients,subject=subject,message=message,cc=cc)     
    except Exception as e:
        print(str(e))




@frappe.whitelist()
def send_email_with_css(doc=None,method=None):
    # Recipient email address
    to_email = "s.upare@cloudextel.com"

    # Email subject
    subject = "Sample Email with Inline CSS"

    # Email body with inline CSS
    html_content = """
    <html>
    <head>
        <style>
            /* Add your CSS styles here */
            body {
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                color: #333;
                padding: 20px;
            }

            h1 {
                color: #4285f4;
            }

            p {
                font-size: 16px;
                line-height: 1.5;
            }
        </style>
    </head>
    <body>
        <h1>Hello, Frappe!</h1>
        <p>This is a sample email with inline CSS styles.</p>
        <p>You can customize the styles in the &lt;style&gt; tag above.</p>
    </body>
    </html>
    """

    # Send the email
    frappe.sendmail(
        recipients=[to_email],
        subject=subject,
        message=html_content,
        cc=["samarthupare1935@gmail.com"]
    )

    print('SHEHEHEH',to_email,subject,html_content)
