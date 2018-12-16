import json

from gssp_experiments.database import cnx, cursor_dict as cursor


def get_role(guild_id, role_name):
    cnx.commit()
    query = "SELECT * FROM `gssp`.`roles` WHERE `role_name` = %s AND `guild_id` = %s"
    cursor.execute(query, (role_name, guild_id))
    members = []
    try:
        a = cursor.fetchall()[0]
        members += json.loads(a['role_assignees'])
    except IndexError:
        return None
    a['members'] = members
    return a

def get_roles(guild_id, limit_to_joinable=True):
    cnx.commit()
    if limit_to_joinable:
        query = "SELECT * FROM `gssp`.`roles` WHERE `guild_id` = %s AND `is_joinable` = 1"
    else:
        query = "SELECT * FROM `gssp`.`roles` WHERE `guild_id` = %s"
    cursor.execute(query, (guild_id, ))
    return cursor.fetchall()



def get_user(user_id):
    cnx.commit()  # we run this just to make sure we have nothing pending
    query = "SELECT * FROM gssp.ping_settings WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    return cursor.fetchone()
