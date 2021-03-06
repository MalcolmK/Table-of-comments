import sublime, sublime_plugin, re

""" Plugin to create a quick panel lookup that lets you jump between comment titles"""

#
# Text Commands
#
class table_of_comments_command(sublime_plugin.TextCommand):

	def run(self, edit, move=None):
		if move != None:
			return self.traverse_comments(move)
		else:
			view = self.view
			self.create_toc(view, edit);
			titles = self.get_comment_titles(view, 'string')
			self.disabled_packages = titles
			self.window = sublime.active_window()
			self.window.show_quick_panel(self.disabled_packages, self.on_list_selected_done)

	# Allows moving up and down through comments
	def traverse_comments(self, move):
		view   = self.view
		titles = self.get_comment_titles(view)
		sel    = view.sel()
		if len(sel) == 1:
			current_line_no, col_no = view.rowcol(sel[0].b)
			for x in range(len(titles)):
				item = titles[x]
				if move == 'up': # moving up
					if item['line'] < current_line_no:
						if x+1 < len(titles):
							if titles[x+1]['line'] >= current_line_no:
								return self.on_list_selected_done(x)
						else:
							return self.on_list_selected_done(x)
				else:	# moving down
					if item['line'] > current_line_no:
						return self.on_list_selected_done(x)

	#
	# Table TOC tag
	#
	def get_toc_region(self, view):
		title = get_setting('toc_title', str)
		pattern = r'\/\*(\s|\*)*'+title+r'[^\/]*\/'
		matches = view.find_all(pattern)
		for region in (matches):
			return region
		return None

	def create_toc(self, view, edit):
		region = self.get_toc_region(view)
		if region:
			#for region in (matches):
			toc = self.compile_toc(view)
			existing = view.substr(region)
			if existing != toc:
				view.replace(edit, region, toc)

	def compile_toc(self, view):
		titles = self.get_comment_titles(view, 'string')
		title  = get_setting('toc_title', str)
		start  = get_setting('toc_start', str)
		line   = get_setting('toc_line', str)
		end    = get_setting('toc_end', str)
		front  = "\n"+ line
		output = start + front + title + front

		for title in titles:
			comment_level = title.count('-') + 1
			try:
				level = int(get_setting('toc_level', int))
				if level >= comment_level:
					output += front + title
			except TypeError:
				output += front + title

		output+= "\n"+end
		return output

	#
	# Jump list quick menu
	#

	def on_list_selected_done(self, picked):
		if picked == -1:
			return
		titles = self.get_comment_titles(self.view)
		row = titles[picked]['line']
		point = self.view.text_point(row, 0)
		line_region = self.view.line(point)
		self.view.sel().clear()
		self.view.sel().add(line_region.b)
		self.view.show_at_center(line_region.b)

	def get_comment_titles(self, view, format='dict'):
		level_char    = get_setting('level_char', str)
		comment_chars = get_setting('comment_chars', str)
		comment_chars = list(comment_chars)
		comment       = 'DIV'.join(comment_chars)
		start         = r'\s|'+re.escape(comment).replace('DIV', '|')

		# Original attempt
		#pattern = '^('+start+')*?('+format_pattern(level1)+'|'+format_pattern(level2)+'|'+format_pattern(level3)+')\s*?(\w|\s|-)+('+start+')*?$'

		# Allowed more characters within the comment title - thanks @ionutvmi!
		#pattern    = r'^('+start+')*?('+format_pattern(level1)+'|'+format_pattern(level2)+'|'+format_pattern(level3)+')\s*?(\w|\s|[-.,;\'"|{}<?\/\\\\*@#~!$%^=\(\)\[\]])+('+start+')*?$'

		# Allows unlimited number of comment title depths - thanks @MalcolmK!
		pattern    = r'^('+start+')*?('+format_pattern(level_char)+'+)\s*?(\w|\s|[-.,;:\'"|{}<?\/\\\\*@#~!$%^=\(\)\[\]])+('+start+')*?$'
		matches   = view.find_all(pattern)
		results   = []
		toc_title = get_setting('toc_title', str)

		for match in matches:
			bits = view.lines(match)	# go through each line
			for region in bits:
				# Ensure it's comment or source
				if not self.is_scope_or_comment(view, region):
					continue

				if self.is_in_toc_region(view, region):
					continue

				#line = view.substr(view.line(region.b))
				line = view.substr(region)
				#line = view.substr(sublime.Region(region.a, view.line(region.b).b))

				if level_char in line:
					# Format the line as a label
					line = line.replace('/*', '').replace('*/', '')
					for char in comment_chars:
						line = line.replace(char, '')

					# Replace level char with toc char
					line = self.replace_level_chars(line)

					# Get the position
					if line!='' and line!=toc_title:
						line_no, col_no = view.rowcol(region.b)
						if format == 'dict':
							results.append( {'label':line, 'line':line_no} )
						else:
							results.append( line )
		return results

	def is_in_toc_region(self, view, region):
		toc_region = self.get_toc_region(view)
		if toc_region:
			if region.a > toc_region.a and region.a < toc_region.b:
				return True
		return False

	def is_scope_or_comment(self, view, region):
		scope = view.scope_name(region.a)
		if scope.find('comment.') < 0 and scope.find('source.') < 0:
			return False
		return True

	def replace_level_chars(self, line):
		level_char = get_setting('level_char', str)
		toc_char = get_setting('toc_char', str)
		line = line.replace(level_char+' ', ' ')
		line = line.replace(level_char, toc_char).strip()
		return line


#
# Helpers
#

def format_pattern(pattern):
	pattern = re.escape(pattern)
	pattern = pattern.replace('\>', '>')
	return pattern

def get_setting(name, typeof=str):
	settings = sublime.load_settings('tableofcomments.sublime-settings')
	setting = settings.get(name)
	if setting:
		if typeof == str:
			return setting
		if typeof == bool:
			return setting == True
		elif typeof == int:
			return int(settings.get(name, 500))
	else:
		if typeof == str:
			return ''
		else:
			return None
