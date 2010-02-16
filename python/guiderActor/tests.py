import Queue

from guiderActor import *
import guiderActor.myGlobals as myGlobals
import masterThread

def mycall(actor=None, forUserCmd=None, cmdStr=None):
	pass

def mydiag(s):
	print 'diag:', s

def mywarn(s):
	print 'warn:', s

def myinform(s):
	print 'inform:', s

def myfail(s):
	print 'fail:', s

def myrespond(s):
	print 'respond:', s

if __name__ == '__main__':

	# Generic duck-type object
	class ducky(object):
		pass

	mq = Queue.Queue(0)
	queues = {MASTER: mq,
			  GCAMERA: Queue.Queue(0),
			  }

	actor = ducky()
	actor.cmdr = ducky()
	actor.cmdr.call = mycall
	actor.bcast = ducky()
	actor.bcast.warn = mywarn
	actor.bcast.diag = mydiag

	myGlobals.actorState = ducky()
	myGlobals.actorState.timeout = 0
	myGlobals.actorState.models = {}
	tcc = ducky()
	tcc.keyVarDict = {}
	myGlobals.actorState.models['tcc'] = tcc
	mcp = ducky()
	mcp.keyVarDict = {}
	myGlobals.actorState.models['mcp'] = mcp
	myGlobals.actorState.tccState = ducky()
	myGlobals.actorState.tccState.halted = False
	myGlobals.actorState.tccState.goToNewField = False

	cmd = ducky()
	cmd.inform = myinform
	cmd.warn = mywarn
	cmd.fail = myfail
	cmd.respond = myrespond

	m = Msg(Msg.EXIT, cmd)
	mq.put(m)
	masterThread.main(actor, queues)

	
