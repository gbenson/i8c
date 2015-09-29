from i8c import logger
from i8c import operations
from i8c.operations import PlusUConst, SyntheticGoto
from i8c import types
import inspect

# The primary goal of these optimizations is to reduce the instruction
# count, to aid consumers using interpreters to execute notes.  The
# secondary goal of these optimizations is to reduce the size of the
# bytecode in cases where this does not conflict with the primary goal
# of reducing instruction count.

debug_print = logger.debug_printer_for(__name__)

class Optimizer(object):
    """Base class for all optimizers.
    """

    def visit_toplevel(self, toplevel):
        for node in toplevel.functions:
            node.accept(self)

    def debug_print_hit(self, location):
        if debug_print.enabled:
            optimization = inspect.stack()[1][0].f_code.co_name
            for prefix in ("__", "try_"):
                if optimization.startswith(prefix):
                    optimization = optimization[len(prefix):]
            debug_print("%s: %s\n" % (location.fileline, optimization))

class BlockOptimizer(Optimizer):
    """Optimizations performed before serialization.
    """

    def visit_function(self, function):
        self.visited = {}
        function.entry_block.accept(self)

    def visit_basicblock(self, block):
        if self.visited.get(block, False):
            return
        self.visited[block] = True
        self.try_all_optimizations(block)
        for block in block.exits:
            block.accept(self)

    def try_all_optimizations(self, block):
        self.try_eliminate_cmp_bra_const_const(block)
        self.try_eliminate_lit0_cmp_bra(block)
        self.try_peephole(block, self.try_eliminate_identity_math, 2)
        self.try_peephole(block, self.try_use_plus_uconst, 2)

    def __tecbcc_helper(self, block):
        """Helper for try_eliminate_cmp_bra_const_const.
        """
        if len(block.entry_stacks) != 1:
            return
        if len(block.ops) < 2:
            return
        if not block.ops[0].is_load_constant:
            return
        constant = block.ops[0]
        if constant.type.basetype != types.INTTYPE:
            return
        return constant.value

    def try_eliminate_cmp_bra_const_const(self, block):
        """Optimize cases where the blocks following a conditional
        branch load the constants that the comparison pushed to the
        stack.

        This is relevant for libpthread notes.  All the libthread_db
        functions that the libpthread notes replace return a td_err_e
        error code defined as:

          typedef enum {
            TD_OK,  /* No error.  */
            TD_ERR, /* General error.  */
            ...     /* Specific errors.  */
          } td_err_e;

        Some libthread_db functions call proc_service functions which
        return a similar ps_err_e error code:

          typedef enum {
            PS_OK,  /* No error.  */
            PS_ERR, /* General error.  */
            ...     /* Specific errors.  */
          } ps_err_e;

        Note that TD_OK == PS_OK == 0 and TD_ERR == PS_ERR == 1.

        This optimizer replaces code of the following pattern:

            call        /* Some proc_service function.  */
            load PS_OK  /* == 0 */
            bne fail
            load TD_OK  /* == 0 */
            return
          fail:
            load TD_ERR /* == 1 */
            return

        With this:

            call        /* Some proc_service function.  */
            load PS_OK
            ne
        """
        # Does the block end with "comparison, branch"?
        if len(block.ops) < 2:
            return
        if not block.ops[-1].is_branch:
            return
        if not block.ops[-2].is_comparison:
            return

        # Do the successors start with "const 0" and "const 1"?
        constants = map(self.__tecbcc_helper, (block.nobranch_exit,
                                               block.branched_exit))
        if 0 not in constants or 1 not in constants:
            return

        # Are the successors otherwise the same?
        if block.exits[0].exits != block.exits[1].exits:
            return
        try:
            if block.exits[0].ops[1:] != block.exits[1].ops[1:]:
                return
        except NotImplementedError, e:
            debug_print("warning: missed an optimization?"
                        + " (implement %s)\n" % e)
            return

        self.debug_print_hit(block.ops[-1])

        # Reverse the comparison if necessary
        if constants == [1, 0]:
            block.ops[-2].reverse()

        # Lose one of the successor blocks (doesn't matter which)
        dead_block = block.exits.pop()
        dead_block.entry_stacks.pop(block)
        assert not dead_block.entry_stacks

        # Reduce the branch to a goto
        block.ops[-1] = SyntheticGoto(block.ops[-1])

        # Move the the remaining successor and drop the ConstOp.
        # This messes with the types a bit (what was an INTTYPE
        # is now a BOOLTYPE) but that doesn't matter once it's
        # bytecode.
        [block] = block.exits
        removed_op = block.ops.pop(0)
        assert removed_op.is_load_constant

    def try_eliminate_lit0_cmp_bra(self, block):
        # Does the block end with "load 0, {eq,ne}, branch"?
        if len(block.ops) < 3:
            return
        if not block.ops[-1].is_branch:
            return
        if not block.ops[-2].is_comparison:
            return
        if block.ops[-2].dwarfname not in ("eq", "ne"):
            return
        if not block.ops[-3].is_load_constant:
            return
        if block.ops[-3].value != 0:
            return

        self.debug_print_hit(block.ops[-2])

        # Reverse the branch if necessary
        if block.ops[-2].dwarfname == "eq":
            block.ops[-1].exits.reverse()

        # Remove the load and the comparison
        removed_op = block.ops.pop(-3)
        assert removed_op.is_load_constant
        removed_op = block.ops.pop(-2)
        assert removed_op.is_comparison

    def try_peephole(self, block, action, size):
        start = 0
        while True:
            start = self.__try_peephole(block, action, size)
            if start is None:
                break

    def __try_peephole(self, block, action, size):
        """Helper for try_peephole.
        """
        for index in xrange(len(block.ops) - size):
            if action(block, index):
                return index

    IDENTITIES = {
        "plus": 0, "minus": 0, "mul": 1,
        "div": 1, "shl": 0, "shr": 0,
        "shra": 0, "or": 0, "xor": 0}

    def try_eliminate_identity_math(self, block, index):
        if not block.ops[index].is_load_constant:
            return False
        opname = getattr(block.ops[index + 1], "dwarfname", None)
        if opname is None:
            return False
        identity = self.IDENTITIES.get(opname, None)
        if identity is None:
            return False
        if block.ops[index].value != identity:
            return False

        self.debug_print_hit(block.ops[index + 1])

        # Remove the operations
        removed_op = block.ops.pop(index + 1)
        assert removed_op.dwarfname == opname
        removed_op = block.ops.pop(index)
        assert removed_op.is_load_constant

        return True

    def try_use_plus_uconst(self, block, index):
        if not block.ops[index].is_load_constant:
            return False
        if not block.ops[index + 1].is_add:
            return False

        self.debug_print_hit(block.ops[index])

        # Insert the plus_uconst
        block.ops[index] = PlusUConst(block.ops[index])

        # Remove the add
        removed_op = block.ops.pop(index + 1)
        assert removed_op.is_add

        return True

class StreamOptimizer(Optimizer):
    """Optimizations performed after serialization.
    """

    def visit_function(self, function):
        function.ops.accept(self)

    def visit_operationstream(self, stream):
        while True:
            if self.try_remove_multijump(stream):
                continue
            if self.try_remove_goto_next(stream):
                continue
            break

    def try_remove_multijump(self, stream):
        for index, op in stream.items():
            target = stream.jumps.get(op, None)
            if target is None:
                continue
            if not target.is_goto:
                continue

            self.debug_print_hit(op)
            stream.retarget_jump(op, stream.jumps[target])
            return True
        return False

    def try_remove_goto_next(self, stream):
        for index, op in stream.items():
            if index + 1 == len(stream.ops):
                continue
            if not op.is_goto:
                continue
            if stream.labels.get(op, None) is not None:
                continue
            if stream.jumps[op] is not stream.ops[index + 1]:
                continue

            self.debug_print_hit(op)
            stream.remove_by_index_op(index, op)
            return True
        return False
