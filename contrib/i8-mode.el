;;; i8-mode.el --- Emacs major mode for editing I8; -*- lexical-binding:t -*-

;; Copyright (C) 2015-16 Red Hat, Inc.

;; Maintainer: infinity@sourceware.org
;; Author: Gary Benson <gbenson@redhat.com>
;; Keywords: languages i8 infinity modes
;; Version: 1.0

;; This file is part of the Infinity Note Compiler.

;; The Infinity Note Compiler is free software: you can redistribute it
;; and/or modify it under the terms of the GNU General Public License
;; as published by the Free Software Foundation, either version 3 of
;; the License, or (at your option) any later version.

;; The Infinity Note Compiler is distributed in the hope that it will
;; be useful, but WITHOUT ANY WARRANTY; without even the implied
;; warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
;; See the GNU General Public License for more details.

;; You should have received a copy of the GNU General Public License
;; along with the Infinity Note Compiler.  If not, see
;; <http://www.gnu.org/licenses/>.

;; KNOWN BUGS:
;; * "<" and ">" should be string quotes too.
;; * only the first and last types in "returns" get highlighted.
;; * multi-line comments don't line up without manual adjustment.

;;; Code:

(defvar i8-mode-syntax-table
  (let ((table (make-syntax-table)))
    ;; C++-style comments.
    (modify-syntax-entry ?/  ". 124" table)
    (modify-syntax-entry ?*  ". 23b" table)
    (modify-syntax-entry ?\n ">"     table)
    ;; Symbol constituents.
    (modify-syntax-entry ?_  "_"     table)
    table)
  "Syntax table for i8-mode buffers.")

(defconst i8-font-lock-keywords
  `(,(rx symbol-start
         (or
	  ;; Keywords.
	  "argument" "define" "extern" "returns" "typedef" "wordsize"
	  ;; Operators.
	  "abs" "add" "and" "beq" "bge" "bgt" "ble" "blt" "bne" "call"
	  "cast" "deref" "div" "drop" "dup" "eq" "ge" "goto" "gt" "le"
	  "load" "lt" "mod" "mul" "name" "ne" "neg" "not" "or" "over"
	  "pick" "return" "rot" "shl" "shr" "shra" "sub" "swap" "xor")
         symbol-end)
    ;; Function names.
    (,(rx (group (1+ (or word ?_)))
	  "::"
	  (group (1+ (or word ?_))))
     (1 font-lock-function-name-face)
     (2 font-lock-function-name-face))
    ;; Short function names in "call" statements.
    (,(rx "call"
	  (1+ space)
	  (0+ (group (1+ not-newline) ","))
	  (0+ space)
	  (group (1+ (or word ?_))))
     (2 font-lock-function-name-face))
    ;; Types in "returns" statements.
    ;; XXX only the first and last types get highlighted :(
    (,(rx "returns" (1+ space) (group (1+ (or word ?_))))
     (1 font-lock-type-face))
    (,(rx "returns"
    	  (1+ space)
    	  (1+ not-newline)
    	  ","
    	  (0+ space)
    	  (group (1+ (or word ?_))))
     (1 font-lock-type-face))
    ;; Names and types in "argument", "extern" and "typedef"
    ;; statements.  Note that "extern func" with "::" gets
    ;; handled by the generic function name matcher above.
    (,(rx (or "argument" "extern" "typedef")
    	  (1+ space)
    	  (group (1+ not-newline))
    	  (1+ space)
    	  (group (1+ (or word ?_))))
     (1 font-lock-type-face)
     (2 font-lock-variable-name-face))
    ;; Types in "deref" statements.
    (,(rx "deref"
    	  (1+ space)
    	  (0+ (group (1+ not-newline) ","))
    	  (0+ space)
    	  (group (1+ (or word ?_))))
     (2 font-lock-type-face))
    ;; Labels.
    (,(rx (group (1+ (or word ?_))) ":" (not (any ":")))
     (1 font-lock-constant-face))
    ;; Branch targets.
    (,(rx (or "beq" "bge" "bgt" "ble" "blt" "bne" "goto")
    	  (1+ space)
    	  (0+ (group (1+ not-newline) ","))
    	  (0+ space)
    	  (group (1+ (or word ?_))))
     (2 font-lock-constant-face))
    ;; Preprocessor statements.
    (,(rx line-start
    	  (group
    	   "#"
    	   (0+ space)
    	   (1+ (or word ?_))))
     (1 font-lock-preprocessor-face)))
  "Font lock keywords for i8-mode buffers.")

;;;###autoload (add-to-list 'auto-mode-alist '("\\.i8\\'" . i8-mode))

;;;###autoload
(define-derived-mode i8-mode prog-mode "I8"
  "Major mode for editing I8"
  :syntax-table i8-mode-syntax-table
  (setq-local font-lock-defaults '(i8-font-lock-keywords)))

;;; i8-mode.el ends here
