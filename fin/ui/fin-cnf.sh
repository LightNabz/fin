# ============================================================
#  fin Command-Not-Found Shell Integration
#  Selachii Project © 2026 — GPL v3
# ============================================================
#
#  To enable, add this to your .bashrc or .zshrc:
#    source /etc/fin/fin-cnf.sh
#

# BASH integration
command_not_found_handle() {
    local cmd="$1"
    # Call fin cnf
    # We use 'fin' directly, assuming it's in PATH
    fin cnf "$cmd" 2>/dev/null
    
    # Return 127 to keep standard Bash behavior (Command not found)
    return 127
}

# ZSH integration
command_not_found_handler() {
    local cmd="$1"
    fin cnf "$cmd" 2>/dev/null
    return 127
}
