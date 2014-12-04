#! /usr/bin/python
"""
Folder Comparer 1.2.0. Copyright (c) 2005-2012 Mark H. P. Lord.

To compare two folders:
    foldercomp.py [options...] <new_folder> <old_folder>

Options:
    -timediff <seconds>
        Enables comparison of file times and sets the tolerance. If the
        modification times of two files differ by less than the number of
        seconds, the times will be considered equal. So if you know that the
        clock on a certain server is out by 30 seconds, use -timediff 30.

    -showequal
        Causes foldercomp to print the names of all files/folders that are
        unchanged between the two locations.

    -nocontent
        Don't compare the content of each file, just their sizes.
"""

import sys
import os

IGNORE_FILENAMES = [".", "..", ".DS_Store", "Thumbs.db"]

def equal_file_contents(path1, path2):
	block_size = 1*1024*1024
	fh1 = open(path1, "rb")
	fh2 = open(path2, "rb")
	equal = True
	while True:
		block1 = fh1.read(block_size)
		block2 = fh2.read(block_size)
		if block1 != block2:
			equal = False
			break
		if len(block1) != block_size:
			break
	fh2.close()
	fh1.close()
	return equal

#
# FolderComparerDifference
#

class FolderComparerDifference:
	EQUAL = 0
	CREATED = 1
	DELETED = 2
	FILE_BECAME_FOLDER = 3
	FOLDER_BECAME_FILE = 4
	NEWER = 5
	OLDER = 6
	LARGER = 7
	SMALLER = 8
	EQUAL_FOLDER = 9  # This is used instead of "equal" for folders
	CREATED_FOLDER = 10
	REMOVED_FOLDER = 11
	EQUAL_LINKS = 12
	DIFFERING_LINKS = 13
	MODIFIED = 14

	NAMES = {
		EQUAL : "Equal",
		CREATED : "Created",
		DELETED : "Deleted",
		FILE_BECAME_FOLDER : "File became folder",
		FOLDER_BECAME_FILE : "Folder became file",
		NEWER : "Newer",
		OLDER : "Older",
		LARGER : "Larger",
		SMALLER : "Smaller",
		EQUAL_FOLDER : "Equal folder",
		CREATED_FOLDER : "Created folder",
		REMOVED_FOLDER : "Removed folder",
		EQUAL_LINKS : "Equal links",
		DIFFERING_LINKS : "Differing links",
		MODIFIED : "Modified"
	}

	EQUAL_DIFFTYPES = [ EQUAL, EQUAL_FOLDER, EQUAL_LINKS ]

#
# FolderComparerCallback
#

class FolderComparerCallback:
	def __init__(self):
		pass

#
# SimpleFolderComparerCallback
#

class SimpleFolderComparerCallback (FolderComparerCallback):
	"""Very simple implementation of FolderComparerCallback that just
	   prints the differences in a format that's easy to grep."""

	def __init__(self, showequal = False):
		self.showequal = showequal
		FolderComparerCallback.__init__(self)

	def difference(self, difftype, displayname):
		if not self.showequal and difftype in FolderComparerDifference.EQUAL_DIFFTYPES:
			return

		print("%-18s: %s" % (FolderComparerDifference.NAMES[difftype], displayname))

#
# FolderComparer
#

class FolderComparer:
	"""Encapsulates the folder comparison logic and its options."""

	def __init__(self):
		self.timeepsilon = 0
		self.compare_times = False
		self.showequal = False
		self.compare_content = True
		self.callback = None

	def set_compare_times(self, value):
		self.compare_times = value

	def set_time_epsilon(self, value):
		self.timeepsilon = value

	def set_show_equal_files(self, value):
		self.showequal = value

	def set_compare_content(self, value):
		self.compare_content = value

	def set_callback(self, value):
		self.callback = value

	def need_callback(self):
		if self.callback == None:
			self.callback = SimpleFolderComparerCallback(self.showequal)

	def report_any_time_difference(self, a, b, filename, displayname):
		if self.compare_times:
			amtime = a.get_mtime(filename)
			bmtime = b.get_mtime(filename)
			if amtime > bmtime + self.timeepsilon:
				self.callback.difference(FolderComparerDifference.NEWER, displayname)
				return True
			elif amtime < bmtime - self.timeepsilon:
				self.callback.difference(FolderComparerDifference.OLDER, displayname)
				return True

		return False

	def folder_item_compare(self, a, filename, b):
		self.need_callback()

		# Work out the display name of the file we're comparing
		if a:
			displayname = a.display_name(filename)
		else:
			displayname = b.display_name(filename)

		# These are used later
		afolder = None
		bfolder = None

		if b == None:
			# No b folder specified, so this file name is new in a
			afolder = a.get_folder(filename)
			if afolder:
				self.callback.difference(FolderComparerDifference.CREATED_FOLDER, displayname)
			else:
				self.callback.difference(FolderComparerDifference.CREATED, displayname)
		elif a == None:
			# No a folder specified, so this file is in b but not a
			bfolder = b.get_folder(filename)
			if bfolder:
				self.callback.difference(FolderComparerDifference.REMOVED_FOLDER, displayname)
			else:
				self.callback.difference(FolderComparerDifference.DELETED, displayname)
		else:
			afolder = a.get_folder(filename)
			bfolder = b.get_folder(filename)

			if (afolder == None) != (bfolder == None):
				# Check to see if the file changed from a file to a directory
				# or vice versa
				if afolder:
					self.callback.difference(FolderComparerDifference.FILE_BECAME_FOLDER, displayname)
				else:
					self.callback.difference(FolderComparerDifference.FOLDER_BECAME_FILE, displayname)
			elif afolder != None:
				# Don't compare modification times or sizes of folders.
				self.callback.difference(FolderComparerDifference.EQUAL_FOLDER, displayname)
			else:
				alink = a.read_link(filename)
				blink = b.read_link(filename)

				if (alink == None) != (blink == None):
					# Link changed to file or vice versa
					if alink:
						self.callback.difference(FolderComparerDifference.LinkBecameFile, displayname)
					else:
						self.callback.difference(FolderComparerDifference.FileBecameLink, displayname)
				elif alink != None:
					if alink == blink:
						self.callback.difference(FolderComparerDifference.EQUAL_LINKS, displayname)
					else:
						self.callback.difference(FolderComparerDifference.DIFFERING_LINKS, displayname)
				else:
					# Compare modification times
					if not self.report_any_time_difference(a, b, filename, displayname):
						# Compare file sizes
						asize = a.get_size(filename)
						bsize = b.get_size(filename)
						if asize > bsize:
							self.callback.difference(FolderComparerDifference.LARGER, displayname)
						elif asize < bsize:
							self.callback.difference(FolderComparerDifference.SMALLER, displayname)
						elif self.compare_content and not equal_file_contents(a.full_name(filename), b.full_name(filename)):
							self.callback.difference(FolderComparerDifference.MODIFIED, displayname)
						else:
							# Everything is the same
							self.callback.difference(FolderComparerDifference.EQUAL, displayname)

		if afolder != None and bfolder != None:
			# Both a and b were supplied and in both of them, filename is a folder.
			# Carry on comparing in that folder.
			self.folder_compare(afolder, bfolder)
		elif afolder != None:
			# In folder a, filename is a folder. In b it's not. Call folder_compare
			# with only the folder in a (folder_compare will print everything it
			# finds as new.)
			self.folder_compare(afolder, None)
		elif bfolder != None:
			# In folder b, filename is a folder. In a it's not. Call folder_compare
			# with only the folder in b (folder_compare will print everything it
			# finds as having been deleted.)
			self.folder_compare(None, bfolder)

	def folder_compare(self, a, b):
		"""Compare two folders, a and b, and output differences. One of a or b
		   can be None, but not both."""

		# Get list of files in a
		if a:
			alist = a.file_list()
		else:
			alist = []

		# Get list of files in b
		if b:
			blist = b.file_list()
		else:
			blist = []

		# Scan a
		for it in alist:
			if it not in blist:
				# File named "it" is not found in b, so b folder is not passed
				# to folder_item_compare
				self.folder_item_compare(a, it, None)
			else:
				# File named "it" exists in both folders, so a and b are both
				# passed to folder_item_compare
				self.folder_item_compare(a, it, b)

		# Scan b for files that are in b but not a
		for it in blist:
			if it not in alist:
				# File named "it" is not found in a, so a folder is not passed
				# to folder_item_compare
				self.folder_item_compare(None, it, b)

#
# Folder
#

class Folder:
	"""A folder that can be rescursively scanned. This is an abstract class."""

	def __init__(self, display_name_path):
		self.display_name_path = display_name_path
		pass

	def display_name(self, shortname):
		return os.path.join(self.display_name_path, shortname)

#
# FileSystemFolder
#

class FileSystemFolder (Folder):
	"""Implementation of Folder for file system folders."""

	def __init__(self, path, display_name_path):
		Folder.__init__(self, display_name_path)
		self.path = path

	def file_list(self):
		list = os.listdir(self.path)
		return [x for x in list if not x in IGNORE_FILENAMES]

	def full_name(self, shortname):
		return os.path.join(self.path, shortname)

	def get_folder(self, shortname):
		fullname = self.full_name(shortname)
		displayname = self.display_name(shortname)
		if os.path.isdir(fullname) and not os.path.islink(fullname):
			return FileSystemFolder(fullname, displayname)
		else:
			return None

	def read_link(self, shortname):
		fullname = self.full_name(shortname)
		if not os.path.islink(fullname):
			return None
		return os.readlink(fullname)

	def get_size(self, shortname):
		return os.path.getsize(self.full_name(shortname))

	def get_mtime(self, shortname):
		return os.path.getmtime(self.full_name(shortname))

#
# Functions
#

def die(msg):
	"""Print an error message, then abort the application."""
	sys.exit(msg)


def usage():
	global __doc__
	sys.exit(__doc__)


def main(args):
	"""foldercomp's entry point when foldercomp is executed (as opposed to
	   when foldercomp is loaded as a module.)"""

	folders = []
	timeepsilon = 0
	compare_times = False
	showequal = 0
	compare_content = True

	i = 0
	while i < len(args):
		arg = args[i]
		lastarg = (i == len(args) - 1)

		addfolder = None

		if arg == '-folder':
			if lastarg:
				die("You need to specify the name of a folder after -folder.")
			i += 1
			addfolder = FileSystemFolder(args[i], '')

		elif arg == '-timediff':
			if lastarg:
				die("You need to specify a time, in seconds, after -timediff.")
			try:
				i += 1
				timeepsilon = int(args[i])
				compare_times = True
			except:
				die("Parameter to -timediff must be an integer.")

		elif arg == '-showequal':
			showequal = True

		elif arg == '-nocontent':
			compare_content = False

		elif arg[0] == '-':
			die("Unknown argument: %s" % (arg))

		else:
			addfolder = FileSystemFolder(arg, '')

		if addfolder:
			if len(folders) == 2:
				die("Too many folders specified. Maximum of two.")
			folders.append(addfolder)

		i += 1

	if len(folders) != 2:
		usage()

	comparer = FolderComparer()
	comparer.set_time_epsilon(timeepsilon)
	comparer.set_compare_times(compare_times)
	comparer.set_show_equal_files(showequal)
	comparer.set_compare_content(compare_content)
	comparer.folder_compare(folders[0], folders[1])


if __name__ == "__main__":
	main(sys.argv[1:])
