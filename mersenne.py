# Mersenne Twister
# based on Wikipedia, retrieved on 2014-10-10
# https://en.wikipedia.org/wiki/Mersenne_twister
#
# I found other Python implementations but they weren't producing the expected
# values, due to improvements and/or bugs. This one is perfectly standard.

pow_2_32 = 2 ** 32  # constant used to find lowest 32 bits

# Create a length 624 array to store the state of the generator
MT = [0 for i in range(624)]
index = 0

# Initialize the generator from a seed
def initialize_generator(seed):
    global pow_2_32
    global MT
    global index
    index = 0
    MT[0] = seed
    for i in range(1, 624):
        MT[i] = (0x6C078965 * (MT[i - 1] ^ (MT[i - 1] >> 30)) + i) % pow_2_32


# Extract a tempered pseudorandom number based on the index-th value,
# calling generate_numbers() every 624 numbers
def extract_number():
    global MT
    global index
    if index == 0:
        generate_numbers()
    y = MT[index]
    y ^= y >> 11
    y ^= (y << 7) & 0x9D2C5680
    y ^= (y << 15) & 0xEFC60000
    y ^= y >> 18

    index = (index + 1) % 624
    return y


# Generate an array of 624 untempered numbers
def generate_numbers():
    global MT
    for i in range(624):
        a = MT[i] & 0x80000000  # bit 31 (32nd bit) of MT[i]
        b = MT[(i + 1) % 624] & 0x7FFFFFFF  # bits 0-30 (first 31 bits) of MT[...]
        y = a + b
        MT[i] = MT[(i + 397) % 624] ^ (y >> 1)
        if y % 2 != 0:
            MT[i] ^= 0x9908B0DF


if __name__ == "__main__":
    # import sys
    pass
