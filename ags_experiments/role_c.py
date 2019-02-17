import json

from gssp_experiments.database import cnx, cursor_dict

update_query = "UPDATE `gssp`.`roles` SET `role_assignees`=%s WHERE `role_id`=%s;"


class DbRole():
    role_id = None
    role_name = None
    pingable = False
    members = None

    def __init__(self, role_id, role_name, pingable = False, members = None, members_json = None):
        self.role_id = role_id
        self.role_name = role_name
        self.pingable = pingable
        self.members = []
        if members is not None:
            self.members = members
        elif members_json is not None:
            members_t = json.loads(members_json)
            for member in members_t:
                self.members.append(dict(member_id = member))

    def get_members(self):
        return self.members

    def save_members(self):
        members_j = json.dumps(self.members)
        cursor_dict.execute(update_query, (members_j, self.role_id))
        cnx.commit()
