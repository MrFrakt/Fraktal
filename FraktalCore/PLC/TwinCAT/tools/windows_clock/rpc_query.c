#include <stdlib.h>
#include "w32time.h"
void* __RPC_USER midl_user_allocate(size_t size) { return calloc(1, size); }
void __RPC_USER midl_user_free(void* pointer) { free(pointer); }
unsigned long QueryStatusSafely(handle_t binding, FraktalW32Status** status) {
 unsigned long result = 0;
 RpcTryExcept { result = FraktalQueryStatus(binding, status); }
 RpcExcept(1) { result = RpcExceptionCode(); }
 RpcEndExcept
 return result;
}
