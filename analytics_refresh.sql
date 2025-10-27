-- lawmaker_tweets 1_tweets_df.csv
select distinct a.pub_date date, DateName(month, DateAdd(month,month(pub_date),-1)) month, year(pub_date) year, b.Chamber chamber, 
d.issue_name, b.display_name, b.person_id, b.party_name, b.party_id party, b.us_state_id state, b.district_no district, e.full_name ,a.comm_content_id from congress_db.dbo.comm_content a 
join legis.dbo.swi_issue_comm_mapping c 
on a.comm_content_id = c.comm_content_id
join legis.rpt.lawmakers_list b 
on a.member_id = b.member_id 
join legis.dbo.swi_issue d 
on c.swi_issue_id = d.swi_issue_id
join legis.dbo.person_alias e
on b.person_id = e.person_id
where a.pub_date > '2021-01-03' and c.swi_issue_id <= 21 and e.is_preferred = 1 and a.comm_type_id = 1

-- congressional_tweet_sentiment old.csv
select distinct a.comm_content_id, a.pub_date, b.Chamber chamber, a.content, b.person_id, b.title, b.first_name, b.last_name, b.display_name, b.party_name,
b.us_state_id, d.issue_name, a.sentiment_score score
from congress_db.dbo.comm_content a 
join legis.dbo.swi_issue_comm_mapping c 
on a.comm_content_id = c.comm_content_id
join legis.rpt.lawmakers_list b 
on a.member_id = b.member_id 
join legis.dbo.swi_issue d 
on c.swi_issue_id = d.swi_issue_id
where a.pub_date > '2021-01-03' and c.swi_issue_id <= 21 and a.comm_type_id = 1


