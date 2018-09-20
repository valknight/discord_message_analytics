import json

from gssp_experiments.database import cnx, cursor_dict as cursor


def get_role(role_name):
    cnx.commit()
    query = "SELECT * FROM `gssp`.`roles` WHERE `role_name` = %s"
    cursor.execute(query, (role_name,))
    members = []
    try:
        a = cursor.fetchall()[0]
        members += json.loads(a['role_assignees'])
    except IndexError:
        return None
    a['members'] = members
    return a


def get_user(user_id):
    cnx.commit()  # we run this just to make sure we have nothing pending
    query = "SELECT * FROM gssp.ping_settings WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    return cursor.fetchone()
