import json
import sys

path = sys.argv[1]
events = json.load(open(path))
puts = [event for event in events if event["kind"] == "request"]
responses = [(event["status"], event["at"]) for event in events
             if event["kind"] == "response" and event["method"] == "PUT"]
polls = [event for event in events if event["kind"].startswith("poll-")]
alerts = [event["alerts"] for event in events if event["kind"] == "alerts-visible"]
print("PUT count:", len(puts))
print("PUT responses:", responses)
print("poll revisions:", sorted({poll["revision"] for poll in polls}))
print("poll entry counts:", sorted({poll["entries"] for poll in polls}))
print("alerts:", alerts)
