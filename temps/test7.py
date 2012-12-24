db=DAL()
db.define_table('Meet',Field('name'))
db.define_table('Team',Field('name'))
db.define_table('Participant_team',
                Field('Meet',db.Meet),
                Field('Team',db.Team))

a=db.Meet.insert(name='here')
b=db.Team.insert(name='snakes')
db.Participant_team.insert(Meet=a,Team=b)
teamStaff = db(db.Meet.id == a).select(
    db.Meet.ALL, db.Team.ALL,
    join = db.Team.on(
        (db.Participant_team.Meet == db.Meet.id) &
        (db.Participant_team.Team == db.Team.id)))

print teamStaff
