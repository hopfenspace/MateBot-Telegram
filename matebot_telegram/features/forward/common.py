"""
Common utilities for MateBot forward handling

The callback query data for this feature and its classes has five components joined by spaces:
 - "forward" to identify this callback query type
 - "communism"|"poll"|refund" to identify the collective operation type
 - {int} as ID of the respective collective to identify it safely
 - "abort"|"ask" as the operation of the forwarding process
   - "abort" to delete the message of the bot (with origin user verification as last element)
   - "ask" will respond with a short notice that the user has to answer this bot
     directly together with the abort button (which is also used for identification later)
 - {int}|"-1" to verify the sender of the reply message to the query ("-1" if not available,
   which is only the case for new forward callback queries, i.e. where the action is "ask")
"""

import re

# Combining the description from above into a single regular
# expression (note that "-1" as identification is only valid for
# the operation "ask", since the user is known as origin of the
# callback query; the user ID is mainly used for user verification
# when an answer is supplied; see class ForwardReplyMessage).
# The leading string "forward" is stripped by the base handler.
CALLBACK_REGEX: re.Pattern = re.compile(r"^(communism|poll|refund) (\d+) (abort|ask) ((?<=abort )\d+|(?<=ask )-1)$")

# In contrast to the above regex, this one is only used for handling reply
# messages. The only expected available button there is the "abort" button,
# therefore this regex can be simplified. However, it must include
# the "forward" prefix now, since it's not stripped by any base class.
MESSAGE_CALLBACK_REGEX: re.Pattern = re.compile(r"^forward (communism|poll|refund) (\d+) (abort) (\d+)$")
