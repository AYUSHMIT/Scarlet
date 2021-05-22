from formulaTree import Formula
import random
import sys
	


def lineToTrace(line):
	lasso_start = None
	try:
		traceData, lasso_start = line.split('::')
	except:
		traceData = line
	trace_vector = [tuple([int(varValue) for varValue in varsInTimestep.split(',')]) for varsInTimestep in
				   traceData.split(';')]

	return (trace_vector, lasso_start)


def lineToWord(line):
	lasso_start = None
	try:
		wordData, lasso_start = line.split('::')
	except:
		wordData = line
	wordVector = list(line.split()[0])
	return (wordVector, lasso_start)  


def convertFileType(operators, wordfile, tracefile=None):
	'''
	converts words file type to trace file type
	'''
	sample = Sample(positive=[], negative=[])
	sample.readFromFile(wordfile)
	one_hot_alphabet = {}
	sample.alphabet.sort()
	for i in range(len(sample.alphabet)):
		one_hot_letter = [str(0)]*len(sample.alphabet)
		letter = sample.alphabet[i]
		one_hot_letter[i] = str(1)
		one_hot_alphabet[letter] = one_hot_letter

	if tracefile==None:
		tracefile = wordfile.rstrip('.words')+'.trace'
	with open(tracefile, 'w') as file:
		for word in sample.positive:
			prop_word = ';'.join([','.join(one_hot_alphabet[letter]) for letter in word.vector])
			file.write(prop_word+'\n')

		file.write('---\n')
		for word in sample.negative:
			prop_word = prop_word = ';'.join([','.join(one_hot_alphabet[letter]) for letter in word.vector])
			file.write(prop_word+'\n')
		file.write('---\n')
		file.write(','.join(operators))


# Use smaller case letters for words
class Trace:
	'''
	defines a sequences of letters, which could be a subset of propositions or symbol from an alphabet
	'''
	def __init__(self, vector, is_word, lasso_start=None):
			
		self.vector = vector
		self.length = len(vector)
		self.lasso_start = lasso_start
		self.is_word = is_word
		if self.lasso_start == None:
			self.is_finite = True
		
		if is_word==False:
			self.vector_str = str(self)

		if lasso_start != None:
			self.is_finite = False
			self.lasso_start = int(lasso_start)
			if self.lasso_start >= self.length:
				raise Exception(
					"lasso start = %s is greater than any value in trace (trace length = %s) -- must be smaller" % (
					self.lasso_start, self.length))

			self.lasso_length = self.length - self.lasso_start
			self.prefix_length = self.length - self.lasso_length

			self.lasso = self.vector[self.lasso_start:self.length]
			self.prefix = self.vector[:self.lasso_start] 


	
	def nextPos(self, currentPos):
		'''
		returns the next position in the trace
		'''
		if self.is_finite:
			if currentPos < self.length:
				return currentPos+1
			else:
				return None
		else:
			if currentPos == self.length - 1:
				return self.lasso_start
			else:
				return currentPos + 1


	
	def futurePos(self, currentPos):
		'''
		returns all the relevant future positions	
		'''
		futurePositions = []
		if self.is_finite:
			futurePositions = list(range(currentPos, self.length))
		else:
			alreadyGathered = set()
			while currentPos not in alreadyGathered:
				futurePositions.append(currentPos)
				alreadyGathered.add(currentPos)
				currentPos = self.nextPos(currentPos)
			futurePositions.append(currentPos)
		return futurePositions

	'''
	def inTracePosition(self, currentpos):
		if currentpos<self.length:
			return currentpos
		else:
			modpos=self.uLength + ((currentpos-self.uLength)%self.vLength)
			return modpos
	'''

	def evaluateFormula(self, formula,letter2pos):
		'''
		evalutates formula on trace
		'''
		#print(self.vector)
		nodes = list(set(formula.getAllNodes()))
		self.truthAssignmentTable = {node: [None for _ in range(self.length)] for node in nodes}


		return self.truthValue(formula, 0,letter2pos)

	def truthValue(self, formula, timestep, letter2pos):
		'''
		evaluates formula on trace starting from timestep
		'''

		futureTracePositions = self.futurePos(timestep)


		tableValue = self.truthAssignmentTable[formula][timestep]
		if tableValue != None:
			return tableValue
		else:
			label = formula.label
			if label == 'true':
				val = True

			elif label == 'false':
				val = False

			elif label.islower():
				if self.is_word:
					val = self.vector[timestep] == label
				else:
					val = self.vector[timestep][letter2pos[label]] # assumes  propositions to be p,q,...
			elif label == '&':
				val = self.truthValue(formula.left, timestep,letter2pos) and self.truthValue(formula.right, timestep,letter2pos)
			
			elif label == '|':
				val = self.truthValue(formula.left, timestep, letter2pos) or self.truthValue(formula.right, timestep, letter2pos)
			
			elif label == '!':
				val = not self.truthValue(formula.left, timestep, letter2pos)
			
			elif label == '->':
				val = not self.truthValue(formula.left, timestep, letter2pos) or self.truthValue(formula.right, timestep, letter2pos)
			
			elif label == 'F':
				val = max([self.truthValue(formula.left, futureTimestep, letter2pos) for futureTimestep in futureTracePositions])
			
			elif label == 'G':
				val = min([self.truthValue(formula.left, futureTimestep, letter2pos) for futureTimestep in futureTracePositions])
			
			elif label == 'U':
				val = max(
					[self.truthValue(formula.right, futureTimestep, letter2pos) for futureTimestep in futureTracePositions]) == True \
					   and ( \
								   self.truthValue(formula.right, timestep, letter2pos) \
								   or \
								   (self.truthValue(formula.left, timestep, letter2pos) and self.truthValue(formula,
																								self.nextPos(timestep), letter2pos)) \
						   )

			elif label == 'X':
				try:
					val = self.truthValue(formula.left, self.nextPos(timestep), letter2pos)
				except:
					val = False
				
			
			self.truthAssignmentTable[formula][timestep] = val
			return val



	def __str__(self):
		#print(self.vector)
		vector_str = [list(map(lambda x: str(int(x)), letter)) for letter in self.vector]
		#rint(vector_str)
		return str(';'.join([','.join(letter) for letter in vector_str]))
	

	def __len__(self):
		 return self.length


		

class Sample:
	'''
	contains the sample of postive and negative examples
	'''
	def __init__(self, positive=[], negative=[], alphabet=[], is_words=True):

		self.positive = positive
		self.negative = negative
		self.alphabet = alphabet
		self.is_words = is_words
		self.num_positives = len(self.positive)
		self.num_negatives = len(self.negative)
		self.operators=[]

	
	def extract_alphabet(self, is_word):
		'''
		extracts alphabet from the words/traces provided in the data
		'''
		alphabet = set()
		

		if self.is_words:
			for w in self.positive+self.negative:
				alphabet = alphabet.union(set(w.vector))
			self.alphabet = list(alphabet)

		else:
			self.alphabet = [chr(ord('p')+i) for i in range(len(self.positive[0].vector[0]))] 
		

		
	

	def word2trace(self, word):
		one_hot_alphabet={}
		for i in range(len(self.alphabet)):
			one_hot_letter = [0]*len(self.alphabet)
			letter = self.alphabet[i]
			one_hot_letter[i] = 1
			one_hot_alphabet[letter] = tuple(one_hot_letter)
		trace_list=[]
		for letter in word:
			trace_list.append(one_hot_alphabet[letter])

		return trace_list



	def readFromFile(self, filename):
		'''
		reads .trace/.word files to extract sample from it
		'''
		self.is_words = ('.words' in filename)
		with open(filename, 'r') as file:
			mode = 0
			count=0
			while True:
				count
				line=file.readline()
				if line=='':
					break

				if line == '---\n':
					mode+=1
					continue

				if mode==0:	
					# can read from both word file type and trace file type
					if self.is_words:
						word_vector, lasso_start = lineToWord(line)
						word = Trace(vector=word_vector, lasso_start=lasso_start, is_word=True)	 	
						self.positive.append(word)
					else:
						trace_vector, lasso_start = lineToTrace(line)
						trace = Trace(vector=trace_vector, lasso_start=lasso_start, is_word=False)	 	
						self.positive.append(trace)

				if mode==1:
					
					if self.is_words:
						word_vector, lasso_start = lineToWord(line)
						word = Trace(vector=word_vector, lasso_start=lasso_start, is_word=True)	 	
						self.negative.append(word)
					else:
						trace_vector, lasso_start = lineToTrace(line)
						trace = Trace(vector=trace_vector, lasso_start=lasso_start, is_word=False)	 	
						self.negative.append(trace)

				if mode==2:
					self.operators = list(line.strip().split(','))
				if mode==3:
					self.alphabet = list(line.split(','))


		if mode != 3:		
				self.extract_alphabet(self.is_words)
		

		self.alphabet.sort()
		self.letter2pos={}
		for i in range(len(self.alphabet)):
			self.letter2pos[self.alphabet[i]]=i
		
		if self.is_words:
			for word in self.positive+ self.negative:
				word.vector= self.word2trace(word.vector)
				word.vector_str= str(word.vector)
				word.is_word = False

	def isFormulaConsistent(self, formula):
		'''
		checks if the sample is consistent with given formula
		'''
		if formula == None:
			return True
		for w in self.positive:
			if w.evaluateFormula(formula,self.letter2pos) == False:
				print('positive', str(w))
				return False

		for w in self.negative:
			if w.evaluateFormula(formula,self.letter2pos) == True:
				print('negative',str(w))
				return False
		return True


	def generator(self, formula=None, filename='generated.words', num_traces=(5,5), length_traces=None, alphabet=['p','q','r'], length_range=(5,15), is_words=True, operators=['G', 'F', '!', 'U', '&','|', '->', 'X']):


		num_positives = 0
		total_num_positives = num_traces[0]
		num_negatives = 0
		total_num_negatives = num_traces[1]
		ver=True
		

		while num_positives<total_num_positives or num_negatives<total_num_negatives:

			if is_words:
				rand_word = ''
				length_word = random.randint(length_range[0], length_range[1])
				for j in range(length_word):
					rand_letter = random.choice(alphabet)
					rand_word+=rand_letter
				final_trace = Trace(rand_word, is_word=is_words)

			else:

				length_trace = random.randint(length_range[0], length_range[1])
				trace_vector = [ [random.randint(0,1) for _ in range(len(alphabet))] for _ in range(length_trace) ]
				final_trace = Trace(trace_vector, is_word=is_words)

			#check
			if formula!=None:
				ver = final_trace.evaluateFormula(formula)

			if num_positives<total_num_positives:
				if ver == True or formula==None:
					self.positive.append(final_trace)
					num_positives+=1
					continue

			if num_negatives<total_num_negatives:
				if ver==False or formula==None:
					self.negative.append(final_trace) 
					num_negatives+=1
			self.operators=operators
			#sys.stdout.write("\rGenerating sample: created %d positives, %d negatives "%(num_positives, num_negatives))
			#sys.stdout.flush()
		self.writeToFile(filename)

	def writeToFile(self, filename):

		with open(filename, 'w') as file:
			for trace in self.positive:

				file.write(str(trace)+'\n')
			file.write('---\n')

			for trace in self.negative:
				file.write(str(trace)+'\n')

			if self.operators!=[]:
				file.write('---\n')
				file.write(','.join(self.operators))
